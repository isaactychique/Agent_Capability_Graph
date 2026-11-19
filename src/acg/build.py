"""Build the project's selected, deduplicated graph directly from both source corpora."""
import argparse
import csv
import json
from pathlib import Path
import sqlite3

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from .rdf.curated import (ACG, SCHEMA, DEFAULT_DB, ROOT, build_graph as curated_graph,
                           entity_uri, load_records, read_collection_date)
from .rdf.registry import build_graph as metadata_graph, iri, rows

from .selection import identity, curated_identity, quality, fingerprint, select_skills, load_selection
from .capabilities import enrich_capabilities

PROV = Namespace('http://www.w3.org/ns/prov#')
OUTPUT = ROOT / 'data/processed/agent_capability_graph.ttl'
SELECTION = ROOT / 'config/corpus_selection.json'
REPORTS = ROOT / 'reports/corpus'
NORMALIZED = ROOT / 'metadata/data/normalized'


def build(refresh=False):
    manifest = json.loads((ROOT / 'data/sources/expanded_sources.json').read_text())
    with sqlite3.connect(f'file:{DEFAULT_DB}?mode=ro', uri=True) as connection:
        records = load_records(connection)
        graph = curated_graph(records, read_collection_date(connection))
    expected = {r['id']: 'MCPServer' for r in manifest['mcp_servers']}
    expected.update({r['id']: 'AgentSkill' for r in manifest['agent_skills']})
    actual = {r['id']: r['type'] for r in records if r['type'] != 'Tool'}
    if actual != expected:
        raise ValueError('SQLite does not match the initial manifest; restore the expanded collection first')
    skills = [s for s in rows(NORMALIZED / 'agent_skills.jsonl') if s.get('disposition') == 'accepted']
    tools = [t for t in rows(NORMALIZED / 'mcp_tools.jsonl') if t.get('disposition') == 'accepted']
    server_ids = {t['server_id'] for t in tools}
    servers = [s for s in rows(NORMALIZED / 'mcp_servers.jsonl')
               if s.get('disposition') == 'accepted' and s['server_id'] in server_ids]
    if {s['server_id'] for s in servers} != server_ids:
        raise ValueError('Tool without accepted parent server')
    selection = load_selection(skills, manifest['agent_skills'], refresh)
    selected_ids = {s['skill_id'] for s in selection['skills']}
    overlap_ids = set(selection['enrich_initial_skill_ids'])
    chosen = [s for s in skills if s['skill_id'] in selected_ids | overlap_ids]
    if {s['skill_id'] for s in chosen} != selected_ids | overlap_ids:
        raise ValueError('A selected or initial overlapping Skill disappeared')
    initial = {curated_identity(s): entity_uri(s['id']) for s in manifest['agent_skills']}
    if any(identity(s['repository_url'], s['skill_path']) in initial for s in chosen if s['skill_id'] in selected_ids):
        raise ValueError('An additional Skill duplicates an initial Skill')
    supplemental = metadata_graph(servers=servers, tools=tools, skills=chosen)
    mapping = {}
    merge_rows = []
    originals = {r['id']: r for r in manifest['mcp_servers']}
    # Explicit aliases use repo and server subdirectory/package context, never repo alone.
    for server in servers:
        sid = server['server_id']
        alias = selection['server_aliases'].get(sid)
        source = iri('server', sid)
        if alias:
            original = originals[alias]
            repo = 'https://github.com/' + original['repository']
            if identity(server['repository_url'], '') != identity(repo, ''):
                raise ValueError(f'Server alias repository mismatch: {sid}')
            if alias == 'filesystem' and not any(p.get('identifier') == '@modelcontextprotocol/server-filesystem'
                                                   for p in server.get('package_identifier', [])):
                raise ValueError('Filesystem alias package mismatch')
            mapping[source] = entity_uri(alias)
        merge_rows.append(('server', str(source), str(mapping.get(source, source)), 'explicit_repo_and_package_alias' if alias else 'additional_server'))
    for tool in tools:
        source = iri('tool', tool['tool_id'])
        parent = mapping.get(iri('server', tool['server_id']), iri('server', tool['server_id']))
        matches = [t for t in graph.objects(parent, ACG.exposesTool)
                   if str(tool['name']) in {str(n) for n in graph.objects(t, SCHEMA.name)}]
        if len(matches) > 1:
            raise ValueError(f'Ambiguous tool identity: {tool["name"]}')
        if matches:
            mapping[source] = matches[0]
        merge_rows.append(('tool', str(source), str(mapping.get(source, source)), 'same_parent_and_tool_name' if matches else 'additional_tool'))
    for skill in chosen:
        source = iri('skill', skill['skill_id'])
        target = initial.get(identity(skill['repository_url'], skill['skill_path']), source)
        mapping[source] = target
        merge_rows.append(('skill', str(source), str(target), 'same_repo_and_skill_path' if source != target else 'additional_skill'))
    datasets = {name: URIRef(f'urn:acg:corpus:{name}') for name in ('curated', 'registry')}
    for node, _, cls in list(graph.triples((None, RDF.type, None))):
        if cls in (ACG.MCPServer, ACG.MCPTool, ACG.AgentSkill):
            graph.add((datasets['curated'], PROV.hadMember, node))
            graph.add((node, PROV.wasDerivedFrom, datasets['curated']))
    for s, p, o in supplemental:
        target = mapping.get(s, s)
        # Keep the initial display name; preserve differing imported names as aliases.
        # Snapshot descriptions and versions retain all of their source documents.
        if p == SCHEMA.name and target != s:
            names = set(graph.objects(target, SCHEMA.name))
            if names and o not in names:
                graph.add((target, SCHEMA.alternateName, o))
                continue
        graph.add((target, p, mapping.get(o, o)))
    for node, _, cls in supplemental.triples((None, RDF.type, None)):
        if cls in (ACG.MCPServer, ACG.MCPTool, ACG.AgentSkill):
            target = mapping.get(node, node)
            graph.add((datasets['registry'], PROV.hadMember, target))
            graph.add((target, PROV.wasDerivedFrom, datasets['registry']))
    for name, dataset in datasets.items():
        graph.add((dataset, RDF.type, PROV.Collection))
        graph.add((dataset, SCHEMA.name, Literal(name)))
    graph.bind('prov', PROV)
    graph.bind('metadata', Namespace('urn:acg:metadata:'))
    for prefix, namespace in supplemental.namespaces():
        if prefix in ('acg', 'schema', 'skos'):
            graph.bind(prefix, namespace)
    if len(set(graph.subjects(RDF.type, ACG.AgentSkill))) != 110:
        raise ValueError('Expected exactly 10 initial + 100 additional Skills')
    enrich_capabilities(graph, records, chosen, mapping)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    # Atomic replace prevents readers observing a partially written Turtle file.
    temp = OUTPUT.with_suffix('.ttl.part')
    graph.serialize(destination=temp, format='turtle')
    temp.replace(OUTPUT)
    REPORTS.mkdir(parents=True, exist_ok=True)
    with (REPORTS / 'identity_mapping.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n'); writer.writerow(['kind','source_id','canonical_id','reason']); writer.writerows(merge_rows)
    with (REPORTS / 'skill_selection.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n'); writer.writerow(['skill_id','name','repository','path','source_kind','revision','metadata_score','decision','evidence'])
        for s in sorted(skills, key=lambda r: (r['repository_url'], r['skill_path'])):
            writer.writerow([s['skill_id'],s['name'],s['repository_url'],s['skill_path'],s.get('source_kind'),s.get('source_revision'),quality(s),selection['decisions'].get(s['skill_id'],'not_in_frozen_selection'),s['source_url']])
    summary = {'graph': str(OUTPUT.relative_to(ROOT)), 'triples': len(graph),
               'counts': {name: len(set(graph.subjects(RDF.type, ACG[name])))
                          for name in ('MCPServer','MCPTool','AgentSkill','CapabilityAssertion')},
               'additional_skills': len(selected_ids), 'initial_skill_enrichments': len(overlap_ids),
               'selected_metadata_servers': len(servers), 'metadata_tools': len(tools),
               'merged_servers': sum(1 for r in merge_rows if r[0]=='server' and r[1]!=r[2]),
               'merged_tools': sum(1 for r in merge_rows if r[0]=='tool' and r[1]!=r[2])}
    (REPORTS / 'summary.json').write_text(json.dumps(summary,indent=2)+'\n', encoding='utf-8')
    print(f"Built {OUTPUT.relative_to(ROOT)}: "
          f"{summary['counts']['MCPServer']} servers, {summary['counts']['MCPTool']} tools, "
          f"{summary['counts']['AgentSkill']} Skills, "
          f"{summary['counts']['CapabilityAssertion']} capability assertions")
    return graph


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--refresh-selection', action='store_true', help='Explicitly recompute the frozen selection of 100 additional Skills')
    args = parser.parse_args()
    build(args.refresh_selection)


if __name__ == '__main__':
    main()
