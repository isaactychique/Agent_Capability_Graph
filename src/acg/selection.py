"""Deterministic, frozen selection of the additional Skills."""
from collections import defaultdict, deque
import hashlib
import json
from .paths import ROOT, SELECTION

def identity(repo, path):
    return (repo.rstrip('/').removesuffix('.git'), path.strip('/'))


def curated_identity(item):
    return identity('https://github.com/' + item['repository'], item['skill_md'])


def quality(record):
    """Transparent metadata score, not an estimate of runtime capability or safety."""
    score = 4 if record.get('source_kind') == 'direct_file' and record.get('source_revision') else 0
    score += bool(record.get('license'))
    score += sum(bool(record.get(k)) for k in ('dependencies', 'compatibility', 'allowed_tools')) * 2
    score += sum(record.get(k) is not None for k in ('has_scripts', 'has_references', 'has_assets'))
    return int(score)


def fingerprint(record):
    payload = json.dumps(record, ensure_ascii=False, sort_keys=True).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()


def select_skills(skills, originals, count=100):
    original_keys = {curated_identity(s) for s in originals}
    overlap = [s for s in skills if identity(s['repository_url'], s['skill_path']) in original_keys]
    groups = defaultdict(list)
    reasons = {}
    seen_hashes = {s['content_hash'] for s in overlap if s.get('content_hash')}
    # Sort first so content-duplicate handling is independent of JSONL row order.
    for s in sorted(skills, key=lambda r: (-quality(r), r['skill_id'])):
        sid = s['skill_id']
        if identity(s['repository_url'], s['skill_path']) in original_keys:
            reasons[sid] = 'enrich_initial_skill'
        elif (not s.get('name') or not s.get('description') or not s.get('source_url')
              or not s.get('skill_path') or not s.get('repository_url')
              or not (ROOT / 'metadata' / s['raw_file']).is_file()):
            reasons[sid] = 'insufficient_metadata_or_missing_cached_evidence'
        elif s.get('content_hash') and s['content_hash'] in seen_hashes:
            reasons[sid] = 'duplicate_content'
        else:
            if s.get('content_hash'):
                seen_hashes.add(s['content_hash'])
            groups[s['repository_url']].append(s)
    selected = []
    # Preserve explicitly documented requirement examples before the general sample.
    priority = sorted((s for group in groups.values() for s in group
                       if any(s.get(k) for k in ('dependencies', 'compatibility', 'allowed_tools'))),
                      key=lambda s: (-quality(s), s['repository_url'], s['skill_path']))
    for s in priority[:count]:
        selected.append(s)
        reasons[s['skill_id']] = 'selected_explicit_requirement_metadata'
    queues = {repo: deque(sorted(group, key=lambda s: (-quality(s), s['skill_path'], s['skill_id'])))
              for repo, group in groups.items()}
    # Prefer direct, revision-pinned sources. Round robin limits a single repository's dominance.
    repos = sorted(queues, key=lambda repo: (-max(quality(s) for s in groups[repo]), repo))
    for direct in (True, False):
        while len(selected) < count:
            added = False
            for repo in repos:
                if len(selected) == count:
                    break
                candidates = queues[repo]
                while candidates and candidates[0]['skill_id'] in reasons:
                    candidates.popleft()
                if not candidates:
                    continue
                s = candidates[0]
                pinned = s.get('source_kind') == 'direct_file' and bool(s.get('source_revision'))
                if bool(pinned) != direct:
                    continue
                candidates.popleft()
                selected.append(s)
                reasons[s['skill_id']] = 'selected_source_quality_repository_round_robin'
                added = True
            if not added:
                break
    if len(selected) != count:
        raise ValueError(f'Only {len(selected)} eligible additional Skills; expected {count}')
    for s in skills:
        reasons.setdefault(s['skill_id'], 'outside_selected_sample')
    return selected, overlap, reasons


def load_selection(skills, originals, refresh=False):
    by_id = {s['skill_id']: s for s in skills}
    if refresh or not SELECTION.exists():
        selected, overlap, reasons = select_skills(skills, originals)
        data = {
            'policy_version': 1,
            'additional_skill_count': 100,
            'policy': 'Keep initial 10 Skills; prioritize requirement metadata, then revision-pinned direct evidence and repository round robin. Exclude duplicate identities/content. Selection is frozen until --refresh-selection.',
            'server_aliases': {
                'srv_8da04d27afcf6c39fe182b2b': 'filesystem',
                'srv_37b4beb11f35bfd13854ad89': 'brave-search',
            },
            'skills': [{'skill_id': s['skill_id'], 'repository_url': s['repository_url'],
                        'skill_path': s['skill_path'], 'record_sha256': fingerprint(s)} for s in selected],
            'enrich_initial_skill_ids': [s['skill_id'] for s in overlap],
            'decisions': reasons,
        }
        SELECTION.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    data = json.loads(SELECTION.read_text(encoding='utf-8'))
    if len(data['skills']) != 100 or len({s['skill_id'] for s in data['skills']}) != 100:
        raise ValueError('Selection must contain exactly 100 distinct additional Skills')
    for entry in data['skills']:
        record = by_id.get(entry['skill_id'])
        if record is None or fingerprint(record) != entry['record_sha256']:
            raise ValueError(f"Selected Skill changed or disappeared: {entry['skill_id']}; review --refresh-selection")
    return data


