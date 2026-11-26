"""Build the selected RDF graph exclusively from the single canonical database."""
import argparse
import csv
import json
from datetime import date

from rdflib import Graph, Literal, Namespace, RDF, URIRef

from .rdf.curated import ACG, SCHEMA, ROOT, build_graph as curated_graph, entity_uri
from .rdf.registry import build_graph as metadata_graph

from .selection import quality
from .capabilities import enrich_capabilities, generate_mappings

PROV = Namespace('http://www.w3.org/ns/prov#')
OUTPUT = ROOT / 'data/processed/agent_capability_graph.ttl'
SELECTION = ROOT / 'config/corpus_selection.json'
REPORTS = ROOT / 'reports/corpus'
from .paths import DATABASE


def build(refresh=False):
    from .database import synchronize, load_graph_inputs
    if refresh:
        synchronize(refresh=True)
    inputs = load_graph_inputs()
    metadata = inputs['metadata']
    manifest = metadata['manifest']
    selection = metadata['selection']
    records = inputs['curated']
    collected_at = metadata.get('collected_at')
    graph = curated_graph(records, date.fromisoformat(collected_at[:10]) if collected_at else None)
    servers, tools, chosen = inputs['servers'], inputs['tools'], inputs['skills']
    skills = inputs['all_skills']
    selected_ids = {s['skill_id'] for s in selection['skills']}
    overlap_ids = set(selection['enrich_initial_skill_ids'])
    supplemental = metadata_graph(servers=servers, tools=tools, skills=chosen, annotations=inputs['annotations'])
    mapping = {URIRef(source): URIRef(target) for source,target in inputs['mapping'].items()}
    merge_rows = inputs['merge_rows']
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
    generate_mappings()
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
    summary = {'graph': str(OUTPUT.relative_to(ROOT)), 'database': str(DATABASE.relative_to(ROOT)), 'triples': len(graph),
               'counts': {name: len(set(graph.subjects(RDF.type, ACG[name])))
                          for name in ('MCPServer','MCPTool','AgentSkill','CapabilityAssertion')},
               'additional_skills': len(selected_ids), 'initial_skill_enrichments': len(overlap_ids),
               'selected_metadata_servers': len(servers), 'metadata_tools': len(tools),
               'merged_servers': sum(1 for r in merge_rows if r[0]=='server' and r[1]!=r[2]),
               'merged_tools': sum(1 for r in merge_rows if r[0]=='tool' and r[1]!=r[2])}
    from .override_history import provenance
    import hashlib
    summary['override_provenance'] = provenance()
    summary['graph_sha256'] = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
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
