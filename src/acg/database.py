"""The single canonical SQLite store, with lossless source observations and a sample profile."""
from collections import defaultdict
from datetime import date
import csv
import json
from pathlib import Path
import sqlite3

from .paths import DATABASE, CURATED_IMPORT, NORMALIZED, REGISTRY, ROOT, REPORTS
from .rdf.curated import entity_uri
from .rdf.registry import iri, rows
from .selection import identity, curated_identity, load_selection

SCHEMA = '''
PRAGMA foreign_keys=ON;
CREATE TABLE entity (
 canonical_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('MCPServer','MCPTool','AgentSkill')),
 name TEXT NOT NULL, parent_id TEXT REFERENCES entity(canonical_id),
 in_sample INTEGER NOT NULL CHECK(in_sample IN (0,1)),
 CHECK((kind='MCPTool' AND parent_id IS NOT NULL) OR (kind!='MCPTool' AND parent_id IS NULL))
);
CREATE TABLE source_record (
 id INTEGER PRIMARY KEY, origin TEXT NOT NULL, source_id TEXT NOT NULL,
 canonical_id TEXT NOT NULL REFERENCES entity(canonical_id), payload_json TEXT NOT NULL,
 match_basis TEXT NOT NULL, UNIQUE(origin,source_id)
);
CREATE TABLE observation (
 id INTEGER PRIMARY KEY, record_id INTEGER NOT NULL REFERENCES source_record(id),
 canonical_id TEXT NOT NULL REFERENCES entity(canonical_id), field TEXT NOT NULL,
 value_json TEXT, source_url TEXT, revision TEXT, evidence_status TEXT
);
CREATE TABLE tool_annotation (
 annotation_id TEXT PRIMARY KEY, tool_id TEXT NOT NULL REFERENCES entity(canonical_id), payload_json TEXT NOT NULL
);
CREATE TABLE imported_observation (id INTEGER PRIMARY KEY, payload_json TEXT NOT NULL);
CREATE TABLE content_inventory (id INTEGER PRIMARY KEY, payload_json TEXT NOT NULL);
CREATE TABLE metadata (key TEXT PRIMARY KEY, value_json TEXT NOT NULL);
CREATE INDEX observation_entity ON observation(canonical_id);
CREATE INDEX source_entity ON source_record(canonical_id);
CREATE VIEW servers AS SELECT * FROM entity WHERE kind='MCPServer';
CREATE VIEW tools AS SELECT * FROM entity WHERE kind='MCPTool';
CREATE VIEW skills AS SELECT * FROM entity WHERE kind='AgentSkill';
CREATE VIEW sample AS SELECT * FROM entity WHERE in_sample=1;
'''


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def repo_key(value):
    return (value or '').rstrip('/').removesuffix('.git').casefold()


def reconcile(curated, servers, tools, skills, manifest, selection):
    """Merge identities; never merge servers solely because they share a repository."""
    entities, mapping, bases = {}, {}, {}
    by_name, by_package = defaultdict(set), defaultdict(set)
    packages_by_entity = defaultdict(set)
    original_servers = {r['id']: r for r in manifest['mcp_servers']}
    skill_keys = {}
    tool_keys = {}

    def register(origin, sid, canonical, kind, name, parent, sample, basis):
        canonical = str(canonical)
        if canonical in entities:
            current = entities[canonical]
            if current['kind'] != kind or current['parent_id'] != parent:
                raise ValueError(f'Inconsistent identity: {canonical}')
            current['in_sample'] |= int(sample)
        else:
            entities[canonical] = dict(canonical_id=canonical, kind=kind, name=name,
                                       parent_id=parent, in_sample=int(sample))
        mapping[(origin, sid)] = canonical
        bases[(origin, sid)] = basis
        return canonical

    for r in curated:
        if r['type'] != 'MCPServer':
            continue
        fields = {f['field']: f['value'] for f in r['fields']}
        canonical = register('curated', r['id'], entity_uri(r['id']), 'MCPServer', fields['name'], None, True, 'initial_identity')
        by_name[(repo_key(fields.get('repository')), fields['name'].casefold())].add(canonical)
    for s in sorted(servers, key=lambda r: r['server_id']):
        sid = s['server_id']; repo = repo_key(s.get('repository_url'))
        packages = {(p.get('registry'), p['identifier']) for p in s.get('package_identifier') or [] if p.get('identifier')}
        alias = selection.get('server_aliases', {}).get(sid)
        matches = set()
        basis = 'distinct_server'
        if alias:
            original = original_servers[alias]
            if repo != repo_key('https://github.com/' + original['repository']):
                raise ValueError(f'Explicit alias has a different repository: {sid}')
            if alias == 'filesystem' and not any(identifier == '@modelcontextprotocol/server-filesystem' for _, identifier in packages):
                raise ValueError('Filesystem package alias mismatch')
            matches = {mapping[('curated', alias)]}; basis = 'explicit_repository_package_alias'
        else:
            for package in packages:
                matches |= by_package[(repo, package)] if repo else set()
            if matches:
                basis = 'same_repository_and_package'
            elif repo:
                matches = {c for c in by_name[(repo, s['name'].casefold())]
                           if not packages or not packages_by_entity[c] or packages & packages_by_entity[c]}
                if matches:
                    basis = 'same_repository_and_name_without_conflicting_packages'
        if len(matches) > 1:
            raise ValueError(f'Ambiguous server identity requires an explicit alias: {sid}')
        canonical = next(iter(matches)) if matches else iri('server', sid)
        canonical = register('registry', sid, canonical, 'MCPServer', s['name'], None, bool(alias), basis)
        by_name[(repo, s['name'].casefold())].add(canonical)
        for package in packages:
            by_package[(repo, package)].add(canonical)
        packages_by_entity[canonical] |= packages
    originals = {curated_identity(r): r for r in manifest['agent_skills']}
    selected_ids = {r['skill_id'] for r in selection['skills']}
    for r in curated:
        if r['type'] != 'AgentSkill':
            continue
        fields = {f['field']: f['value'] for f in r['fields']}
        spec = next(v for v in originals.values() if v['id'] == r['id'])
        key = (repo_key('https://github.com/'+spec['repository']), spec['skill_md'].strip('/'))
        canonical = register('curated', r['id'], entity_uri(r['id']), 'AgentSkill', fields['name'], None, True, 'initial_identity')
        skill_keys[key] = canonical
    for s in sorted(skills, key=lambda r: r['skill_id']):
        key = (repo_key(s['repository_url']), s['skill_path'].strip('/'))
        match = skill_keys.get(key)
        canonical = register('registry', s['skill_id'], match or iri('skill', s['skill_id']), 'AgentSkill',
                             s['name'], None, s['skill_id'] in selected_ids, 'same_repository_and_skill_path' if match else 'distinct_skill')
        skill_keys[key] = canonical
    for r in curated:
        if r['type'] != 'Tool':
            continue
        fields = {f['field']: f['value'] for f in r['fields']}
        parent = mapping[('curated', r['parent'])]
        key = (parent, fields['name'])
        canonical = register('curated', r['id'], tool_keys.get(key) or entity_uri(r['id']), 'MCPTool',
                             fields['name'], parent, entities[parent]['in_sample'], 'same_parent_and_tool_name' if key in tool_keys else 'initial_identity')
        tool_keys[key] = canonical
    for t in sorted(tools, key=lambda r: r['tool_id']):
        parent = mapping[('registry', t['server_id'])]
        key = (parent, t['name']); match = tool_keys.get(key)
        canonical = register('registry', t['tool_id'], match or iri('tool', t['tool_id']), 'MCPTool', t['name'], parent,
                             entities[parent]['in_sample'], 'same_parent_and_tool_name' if match else 'distinct_tool')
        tool_keys[key] = canonical
    return entities, mapping, bases


def synchronize(refresh=False):
    """Atomically import both sources into one database; preserve every source value."""
    imported = json.loads(CURATED_IMPORT.read_text(encoding='utf-8'))
    curated = imported['records']
    manifest = json.loads((ROOT / 'data/sources/expanded_sources.json').read_text())
    expected = {r['id']: 'MCPServer' for r in manifest['mcp_servers']}
    expected.update({r['id']: 'AgentSkill' for r in manifest['agent_skills']})
    if {r['id']: r['type'] for r in curated if r['type'] != 'Tool'} != expected:
        raise ValueError('Curated import does not match the original manifest')
    def accepted(file):
        return [r for r in rows(NORMALIZED/file) if r.get('disposition') == 'accepted']
    servers=accepted('mcp_servers.jsonl'); tools=accepted('mcp_tools.jsonl'); skills=accepted('agent_skills.jsonl')
    selection = load_selection(skills, manifest['agent_skills'], refresh)
    entities, mapping, bases = reconcile(curated, servers, tools, skills, manifest, selection)
    expected_skills = len(manifest['agent_skills']) + selection['additional_skill_count']
    if sum(r['kind']=='AgentSkill' and r['in_sample'] for r in entities.values()) != expected_skills:
        raise ValueError('Sample Skill count differs from configured selection')
    DATABASE.parent.mkdir(parents=True, exist_ok=True)
    temp=DATABASE.with_suffix('.sqlite3.part')
    if temp.exists():temp.unlink()
    try:
        with sqlite3.connect(temp) as db:
            db.executescript(SCHEMA)
            for kind in ('MCPServer','AgentSkill','MCPTool'):
                db.executemany('INSERT INTO entity VALUES(:canonical_id,:kind,:name,:parent_id,:in_sample)',
                               [r for r in entities.values() if r['kind']==kind])
            def put(origin,sid,r):
                canonical=mapping[(origin,sid)]
                cursor=db.execute('INSERT INTO source_record(origin,source_id,canonical_id,payload_json,match_basis) VALUES(?,?,?,?,?)',
                                  (origin,sid,canonical,encode(r),bases[(origin,sid)]))
                record_id=cursor.lastrowid
                fields=r['fields'] if origin=='curated' else [
                    dict(field=k,value=v,source=r.get('source_url'),status=r.get('field_states',{}).get(k,'present' if v is not None else 'unknown')) for k,v in r.items()]
                db.executemany('INSERT INTO observation(record_id,canonical_id,field,value_json,source_url,revision,evidence_status) VALUES(?,?,?,?,?,?,?)',
                               [(record_id,canonical,f['field'],encode(f['value']),f.get('source'),r.get('revision') if origin=='curated' else r.get('source_revision'),f.get('status')) for f in fields])
            for r in curated:put('curated',r['id'],r)
            for records,key in ((servers,'server_id'),(skills,'skill_id'),(tools,'tool_id')):
                for r in records:put('registry',r[key],r)
            for r in rows(REGISTRY/'enriched/capability_annotations.jsonl'):
                db.execute('INSERT INTO tool_annotation VALUES(?,?,?)',(r['annotation_id'],mapping[('registry',r['tool_id'])],encode(r)))
            for file,table in [('source_observations.jsonl','imported_observation'),('skill_contents.jsonl','content_inventory')]:
                db.executemany(f'INSERT INTO {table}(payload_json) VALUES(?)',[(encode(r),) for r in rows(NORMALIZED/file)])
            from .skill_documents import DOCUMENT_SCHEMA, import_documents
            db.execute(DOCUMENT_SCHEMA)
            import_documents(db)
            metadata={'schema_version':2,'collected_at':imported.get('collected_at'),'manifest':manifest,'selection':selection,'curated_collection_metadata':imported.get('collection_metadata',imported.get('repositories',{}))}
            db.executemany('INSERT INTO metadata VALUES(?,?)',[(k,encode(v)) for k,v in metadata.items()])
            if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Broken canonical foreign keys')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('SQLite integrity check failed')
        temp.replace(DATABASE)
    except BaseException:
        if temp.exists():temp.unlink()
        raise
    export_store_report()
    from .capabilities import generate_mappings
    generate_mappings()
    print(f'Synchronized single database: {DATABASE.relative_to(ROOT)}')
    return DATABASE


def connect():
    if not DATABASE.exists():
        raise FileNotFoundError('Unified database missing. Run: python pipeline.py import')
    return sqlite3.connect(f'file:{DATABASE}?mode=ro',uri=True)


def load_graph_inputs():
    """All RDF input comes from this one SQLite database, never from both source folders."""
    with connect() as db:
        metadata={k:json.loads(v) for k,v in db.execute('SELECT key,value_json FROM metadata')}
        selected=db.execute('SELECT s.origin,s.source_id,s.canonical_id,e.kind,s.payload_json,s.match_basis FROM source_record s JOIN entity e USING(canonical_id) WHERE e.in_sample=1 ORDER BY s.origin,s.source_id').fetchall()
        source_skills=[json.loads(p) for (p,) in db.execute("SELECT s.payload_json FROM source_record s JOIN entity e USING(canonical_id) WHERE s.origin='registry' AND e.kind='AgentSkill' ORDER BY s.source_id")]
        annotations=[json.loads(p) for (p,) in db.execute('SELECT a.payload_json FROM tool_annotation a JOIN entity e ON e.canonical_id=a.tool_id WHERE e.in_sample=1 ORDER BY annotation_id')]
    curated=[]; servers=[]; tools=[]; skills=[]; mapping={}; merge_rows=[]
    for origin,sid,canonical,kind,payload,basis in selected:
        record=json.loads(payload)
        if origin=='curated':
            curated.append(record)
        else:
            {'MCPServer':servers,'MCPTool':tools,'AgentSkill':skills}[kind].append(record)
            source=str(iri({'MCPServer':'server','MCPTool':'tool','AgentSkill':'skill'}[kind],sid))
            mapping[source]=canonical
            merge_rows.append(({'MCPServer':'server','MCPTool':'tool','AgentSkill':'skill'}[kind],source,canonical,basis))
    return dict(curated=curated,servers=servers,tools=tools,skills=skills,mapping=mapping,
                merge_rows=merge_rows,annotations=annotations,all_skills=source_skills,metadata=metadata)


def export_store_report():
    folder=REPORTS/'database';folder.mkdir(parents=True,exist_ok=True)
    with connect() as db:
        summary={'database':str(DATABASE.relative_to(ROOT)), 'all_entities':{}, 'sample':{},
                 'source_records':db.execute('SELECT COUNT(*) FROM source_record').fetchone()[0],
                 'observations':db.execute('SELECT COUNT(*) FROM observation').fetchone()[0]}
        for kind in ('MCPServer','MCPTool','AgentSkill'):
            summary['all_entities'][kind]=db.execute('SELECT COUNT(*) FROM entity WHERE kind=?',(kind,)).fetchone()[0]
            summary['sample'][kind]=db.execute('SELECT COUNT(*) FROM entity WHERE kind=? AND in_sample=1',(kind,)).fetchone()[0]
        with (folder/'entities.csv').open('w',newline='',encoding='utf-8') as output:
            writer=csv.writer(output,lineterminator='\n');writer.writerow(['canonical_id','kind','name','parent_id','in_sample'])
            writer.writerows(db.execute('SELECT * FROM entity ORDER BY kind,canonical_id'))
        with (folder/'identity_mapping.csv').open('w',newline='',encoding='utf-8') as output:
            writer=csv.writer(output,lineterminator='\n');writer.writerow(['origin','source_id','canonical_id','match_basis'])
            writer.writerows(db.execute('SELECT origin,source_id,canonical_id,match_basis FROM source_record ORDER BY origin,source_id'))
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    return summary
