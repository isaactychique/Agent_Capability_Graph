"""Counts and annotation coverage; an unannotated entity has unknown capability coverage."""
import json
from rdflib import Graph, Namespace, RDF
from .paths import GRAPH, REPORTS

ACG = Namespace('urn:acg:ontology:')
SCHEMA = Namespace('https://schema.org/')


def coverage(graph):
    result = {}
    for kind in ('MCPServer', 'MCPTool', 'AgentSkill'):
        entities = set(graph.subjects(RDF.type, ACG[kind]))
        candidate = reviewed = derived = missing = 0
        for entity in entities:
            claims = list(graph.objects(entity, ACG.hasCapabilityAssertion))
            if not claims:
                missing += 1
                continue
            if any(str(graph.value(c, ACG.reviewStatus)) == 'reviewed' for c in claims):
                reviewed += 1
            if any(str(graph.value(c, ACG.reviewStatus)) == 'candidate_for_human_review' for c in claims):
                candidate += 1
            if any(list(graph.objects(c, ACG.derivedFromAssertion)) for c in claims):
                derived += 1
        result[kind] = {'total': len(entities), 'with_assertion': len(entities)-missing,
                        'candidate': candidate, 'reviewed': reviewed, 'derived_from_tools': derived,
                        'unclassified': missing}
    return result


def inventory(graph_path=GRAPH):
    graph = Graph().parse(graph_path, format='turtle')
    stats = coverage(graph)
    print(f'Graph: {graph_path}\nTriples: {len(graph)}')
    print('Type       | Total | Annotated | Candidates | Reviewed | Derived from tools | Unclassified')
    for kind, counts in stats.items():
        print(f"{kind:10} | {counts['total']:5} | {counts['with_assertion']:9} | {counts['candidate']:10} | {counts['reviewed']:8} | {counts['derived_from_tools']:18} | {counts['unclassified']:12}")
    print(f"Capability concepts: {len(set(graph.subjects(RDF.type, ACG.Capability)))}")
    print(f"Capability assertions: {len(set(graph.subjects(RDF.type, ACG.CapabilityAssertion)))}")
    print('Candidates require human review. Unclassified means no supported mapping recorded.')
    print('Server annotations are derived from their tool assertions; this is not runtime verification.')
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / 'capabilities/coverage.json').parent.mkdir(parents=True, exist_ok=True)
    (REPORTS / 'capabilities/coverage.json').write_text(json.dumps(stats, indent=2)+'\n', encoding='utf-8')
    return stats
