"""Offline SKILL.md snapshots and source-located candidate extraction.

Documents are imported into SQLite once. Builds never reopen source archives.
Only source-linked pinned archives and complete cached markdown are accepted.
"""
import csv
import hashlib
import json
import re
import zipfile

from .paths import ROOT, REPORTS, raw_path

DOCUMENT_SCHEMA = '''
CREATE TABLE skill_document (
 entity_id TEXT NOT NULL REFERENCES entity(canonical_id), origin TEXT NOT NULL,
 source_url TEXT NOT NULL, revision TEXT, content_sha256 TEXT,
 markdown TEXT, locator TEXT, status TEXT NOT NULL,
 PRIMARY KEY(entity_id,origin,source_url)
);
'''


def import_documents(db):
    """Inventory every Skill source, recording missing bodies rather than guessing."""
    rows = db.execute("""SELECT s.canonical_id,s.origin,s.payload_json FROM source_record s
        JOIN entity e USING(canonical_id) WHERE e.kind='AgentSkill'
        ORDER BY s.origin,s.source_id""").fetchall()
    for entity, origin, payload in rows:
        r = json.loads(payload)
        text = None
        locator = None
        status = 'body_not_cached'
        revision = r.get('revision') if origin == 'curated' else r.get('source_revision')
        if origin == 'curated':
            fields = {f['field']: f for f in r['fields']}
            url = fields['description']['source']
            archive = fields.get('package_archive', {}).get('value')
            if archive:
                path = (ROOT / archive).resolve()
                # Historical unpinned archive names are deliberately not a fallback.
                if not path.is_relative_to(ROOT.resolve()):
                    status = 'invalid_cache_locator'
                elif not revision or revision not in path.name or revision not in url:
                    status = 'unpinned_cache_locator'
                elif path.is_file():
                    try:
                        member = f"{r['id']}/SKILL.md"
                        with zipfile.ZipFile(path) as z:
                            info = z.getinfo(member)
                            if info.file_size > 2_000_000:
                                raise ValueError('Document exceeds import size limit')
                            text = z.read(member).decode('utf-8')
                        locator = f'{archive}!{member}'
                    except (OSError, KeyError, ValueError, UnicodeError, zipfile.BadZipFile):
                        status = 'invalid_archive_document'
        else:
            url = r.get('source_url', '')
            paths = [body_cache_path(url), raw_path(r).resolve()]
            for path in paths:
                if not path.is_relative_to(ROOT.resolve()) or not path.is_file():
                    continue
                snap = json.loads(path.read_text())
                data = snap if path == body_cache_path(url) else snap.get('data', {})
                # Frontmatter-only caches must never be labeled complete documents.
                candidate = data.get('markdown') if isinstance(data, dict) else None
                if (isinstance(candidate, str) and revision and revision in url
                        and snap.get('source_url') == url
                        and data.get('revision') == revision
                        and hashlib.sha256(candidate.encode()).hexdigest() == r.get('content_hash')):
                    text, locator = candidate, str(path.relative_to(ROOT))
                    break
        if text is not None:
            status = 'available'
        digest = hashlib.sha256(text.encode()).hexdigest() if text is not None else None
        db.execute('INSERT INTO skill_document VALUES(?,?,?,?,?,?,?,?)',
                   (entity, origin, url, revision, digest, text, locator, status))


def documents():
    from .database import connect
    with connect() as db:
        if not db.execute("SELECT 1 FROM sqlite_master WHERE name='skill_document'").fetchone():
            raise RuntimeError('Document snapshots missing. Run: python pipeline.py import')
        rows = db.execute('SELECT entity_id,origin,source_url,revision,content_sha256,markdown,locator,status FROM skill_document ORDER BY entity_id,origin,source_url').fetchall()
    return [dict(zip(('entity','origin','source_url','revision','content_sha256','text','locator','status'), row)) for row in rows]


def prose_lines(text):
    """Preserve original offsets; skip frontmatter, fenced examples and exclusions."""
    frontmatter = text.startswith('---\n') or text.startswith('---\r\n')
    fence = None
    offset = 0
    for number, line in enumerate(text.splitlines(keepends=True), 1):
        stripped = line.strip()
        start = offset
        offset += len(line)
        if frontmatter:
            if number > 1 and stripped in ('---', '...'):
                frontmatter = False
            continue
        marker = re.match(r'^(`{3,}|~{3,})', stripped)
        if marker:
            if fence is None:
                fence = marker[1][0]
            elif marker[1][0] == fence:
                fence = None
            continue
        if (fence or re.match(r'^\s*(?:[-*>]\s*)?(?:bad|good|examples?)\s*:', line, re.I)
                or re.search(r"\b(?:not|never|cannot|without|unsupported)\b|don't|doesn't", line, re.I)):
            continue
        yield number, start, line


def located_matches(doc, vocabulary):
    for number, offset, line in prose_lines(doc['text']):
        for concept in vocabulary['concepts']:
            for match in re.finditer(concept['pattern'], line, re.I):
                yield {**{k: concept[k] for k in ('action','object')},
                       **location(doc, number, offset + match.start(), match.group()),
                       'evidence_pattern': re.escape(match.group()),
                       'generator': 'skill_body_task_v1', 'status': 'candidate_for_human_review'}


def location(doc, number, start, quote):
    assert doc['text'][start:start + len(quote)] == quote
    return dict(quote=quote, line=number, start=start, end=start + len(quote),
                content_sha256=doc['content_sha256'], source_url=doc['source_url'],
                origin=doc['origin'], revision=doc['revision'], evidence_type='skill_body')


def fact_candidates(doc):
    """Mentions and explicit requirement statements, never verified support facts."""
    for number, offset, line in prose_lines(doc['text']):
        # Restrict formats to task-oriented prose, rather than every filename mention.
        if re.search(r'\b(read|writ|creat|extract|convert|process|merg|split|edit|support|work)', line, re.I):
            for match in re.finditer(r'\b(?:PDF|DOCX|XLSX|CSV|TSV|spreadsheet)s?\b', line, re.I):
                value = match.group().lower().removesuffix('s') if match.group().lower().endswith('s') else match.group().lower()
                yield {'kind': 'format_mention', 'value': value,
                       **location(doc, number, offset, line.rstrip('\r\n'))}


    # Preserve entire dependency declarations, including conditional install notes.
    # Installation snippets are candidates, not mandatory package requirements.
    section = None
    offset = 0
    frontmatter = doc['text'].startswith('---')
    for number, line in enumerate(doc['text'].splitlines(keepends=True), 1):
        start = offset
        offset += len(line)
        stripped = line.strip()
        if frontmatter:
            if number > 1 and stripped in ('---','...'):
                frontmatter = False
            continue
        heading = re.match(r'^#{1,6}\s+(.+)', stripped)
        if heading:
            title = heading[1].lower()
            section = ('requirement_statement' if title in ('dependencies','prerequisites','requirements')
                       else 'installation_instruction' if title in ('installation','install','setup') else None)
            continue
        if not section or not stripped or stripped.startswith(('```','~~~')):
            continue
        if section == 'installation_instruction' and not re.match(r'^(?:python(?:3)? -m )?(?:pip(?:3)?|npm|uv pip) install\s', stripped):
            continue
        yield {'kind':section, 'value':stripped,
               **location(doc, number, start, line.rstrip('\r\n'))}


def write_document_reports(docs, facts):
    folder = REPORTS / 'capabilities'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'documents.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['entity','origin','source_url','revision','content_sha256','locator','status'], extrasaction='ignore')
        writer.writeheader(); writer.writerows(docs)
    with (folder / 'body_facts.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['entity','kind','value','quote','line','start','end','source_url','revision','content_sha256','status'], extrasaction='ignore')
        writer.writeheader(); writer.writerows(facts)
    available = {d['entity'] for d in docs if d['status']=='available'}
    summary = {'skill_entities':len({d['entity'] for d in docs}), 'with_full_document':len(available),
               'without_full_document':len({d['entity'] for d in docs} - available),
               'fact_candidates':len(facts), 'human_evaluation':'pending'}
    write_review_sample(docs, facts)
    (folder / 'documents.json').write_text(json.dumps(summary, indent=2) + '\n')


def write_review_sample(docs, facts):
    """Create a stable small sample; preserve labels on subsequent refreshes.

    This is a review aid, not a random sample or an estimated accuracy measure.
    """
    rules = json.loads((ROOT / 'config/capability_vocabulary.json').read_text())
    pool = []
    for doc in docs:
        if doc['status'] == 'available':
            for rule in located_matches(doc, rules):
                pool.append(dict(entity=doc['entity'], kind='capability',
                                 value=rule['action']+' '+rule['object'], **rule))
    pool.extend(facts)
    chosen = []
    # One example per entity and candidate kind, up to 12 distinct contexts.
    seen = set()
    for rule in sorted(pool, key=lambda r:(r['kind'],r['entity'],r['start'])):
        key = (rule['entity'],rule['kind'])
        if key not in seen and len(chosen) < 12:
            chosen.append(rule); seen.add(key)
    folder = ROOT / 'data/evaluation'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'skill_body_review.csv'
    fields = ['candidate_id','entity','kind','value','quote','source_url','line','start','end','content_sha256','current_candidate','decision','reviewer','notes']
    previous = {}
    if path.exists():
        with path.open(newline='') as stream:
            previous = {r['candidate_id']:r for r in csv.DictReader(stream)}
    current_ids = {hashlib.sha256(json.dumps([r['entity'],r['kind'],r['value'],r['source_url'],r['content_sha256'],r['start']],ensure_ascii=False).encode()).hexdigest() for r in pool}
    for rule in chosen:
        cid = hashlib.sha256(json.dumps([rule['entity'],rule['kind'],rule['value'],rule['source_url'],rule['content_sha256'],rule['start']],ensure_ascii=False).encode()).hexdigest()
        if cid not in previous:
            previous[cid] = {**rule, 'candidate_id':cid, 'decision':'pending','reviewer':'','notes':''}
    for cid, row in previous.items():
        row['current_candidate'] = 'true' if cid in current_ids else 'false'
    with path.open('w',newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(previous.values())


def body_cache_path(url):
    return ROOT / 'data/imports/registry/skill_documents' / (hashlib.sha256(url.encode()).hexdigest() + '.json')


def collect_documents(limit=None):
    """Fetch pinned direct sources, accepting only the previously recorded SHA-256."""
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timezone
    import socket
    from urllib.error import URLError
    from urllib.parse import urlparse
    from urllib.request import Request, urlopen
    from .database import connect

    with connect() as db:
        records = [json.loads(row[0]) for row in db.execute("""SELECT s.payload_json FROM source_record s
            JOIN entity e USING(canonical_id) WHERE s.origin='registry' AND e.kind='AgentSkill'
            ORDER BY s.source_id""")]
    results, eligible = [], []
    for r in records:
        url = r.get('source_url','')
        parsed = urlparse(url)
        revision = r.get('source_revision') or ''
        parts = parsed.path.strip('/').split('/')
        if (r.get('source_kind') != 'direct_file' or parsed.scheme != 'https'
                or parsed.netloc != 'raw.githubusercontent.com'
                or len(parts) < 4 or parts[2] != revision
                or not re.fullmatch(r'[0-9a-f]{40}', revision)
                or not re.fullmatch(r'[0-9a-f]{64}', r.get('content_hash') or '')):
            results.append(dict(skill_id=r['skill_id'], source_url=url, status='not_pinned_direct_source'))
        else:
            eligible.append(r)
    if limit is not None:
        if limit < 1:
            raise ValueError('Document collection limit must be positive')
        eligible = eligible[:limit]

    def fetch(r):
        url = r['source_url']
        result = dict(skill_id=r['skill_id'], source_url=url, expected_sha256=r['content_hash'])
        path = body_cache_path(url)
        if path.exists():
            try:
                cached = json.loads(path.read_text())
                if (cached.get('source_url') == url and cached.get('revision') == r['source_revision']
                        and hashlib.sha256(cached['markdown'].encode()).hexdigest() == r['content_hash']):
                    return dict(result, status='already_cached')
            except (ValueError, KeyError, TypeError, UnicodeError):
                pass
        try:
            request = Request(url, headers={'User-Agent':'Agent-Capability-Graph/1.0'})
            with urlopen(request, timeout=25) as response:
                raw = response.read(2_000_001)
                if response.geturl() != url:
                    return dict(result, status='unexpected_redirect')
            if len(raw) > 2_000_000:
                return dict(result, status='document_too_large')
            digest = hashlib.sha256(raw).hexdigest()
            if digest != r['content_hash']:
                return dict(result, status='content_hash_mismatch', received_sha256=digest)
            text = raw.decode('utf-8')
            snapshot = dict(source_url=url, revision=r['source_revision'], content_sha256=digest,
                            collected_at=datetime.now(timezone.utc).isoformat(), markdown=text)
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_suffix('.json.part')
            temp.write_text(json.dumps(snapshot, ensure_ascii=False)+'\n')
            temp.replace(path)
            return dict(result, status='downloaded')
        except URLError as exc:
            if isinstance(exc.reason, socket.gaierror):
                raise  # Stop on unavailable networking rather than recording hundreds of failures.
            return dict(result, status='download_error', error=str(exc))
        except (OSError, UnicodeError) as exc:
            return dict(result, status='download_error', error=str(exc))

    # Probe one source before starting concurrent work, making unavailable networking explicit.
    if eligible:
        results.append(fetch(eligible[0]))
        with ThreadPoolExecutor(max_workers=4) as pool:
            for index, result in enumerate(pool.map(fetch, eligible[1:]), 2):
                results.append(result)
                if index % 20 == 0:
                    print(f'Skill documents: {index}/{len(eligible)} processed', flush=True)
    folder = REPORTS / 'capabilities'
    folder.mkdir(parents=True, exist_ok=True)
    (folder/'document_collection.json').write_text(json.dumps(results,indent=2)+'\n')
    from collections import Counter
    print('Document collection:', dict(Counter(r['status'] for r in results)), flush=True)
    return results
