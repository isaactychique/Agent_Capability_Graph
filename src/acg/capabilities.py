"""Evidence-backed task annotations and explicitly derived server capabilities."""
import csv
import hashlib
import json
import re

from rdflib import Literal, Namespace, RDF

from .paths import ROOT, REPORTS
from .rdf.curated import ACG, SCHEMA, entity_uri, source_uri
from .rdf.registry import iri

SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')


def assertion_id(*parts):
    return iri('assertion', hashlib.sha256('\0'.join(map(str, parts)).encode()).hexdigest())


def add_candidate(graph, entity, rule, rule_id, evidence, source, kind):
    match = re.search(rule['evidence_pattern'], evidence, flags=re.I)
    if not match:
        return False
    capability = iri('capability', f"{rule['action']}/{rule['object']}")
    assertion = assertion_id(entity, capability, source, rule_id)
    graph.add((capability, RDF.type, ACG.Capability))
    graph.add((capability, SKOS.prefLabel, Literal(f"{rule['action']} {rule['object']}")))
    graph.add((capability, ACG.capabilityAction, Literal(rule['action'])))
    graph.add((capability, ACG.capabilityObject, Literal(rule['object'])))
    graph.add((entity, ACG.hasCapabilityAssertion, assertion))
    graph.add((assertion, RDF.type, ACG.CapabilityAssertion))
    graph.add((assertion, ACG.assertedCapability, capability))
    graph.add((assertion, ACG.assertionMethod, ACG.curatorMapped))
    graph.add((assertion, ACG.basedOnSource, source))
    graph.add((assertion, ACG.evidenceText, Literal(match.group(0))))
    graph.add((assertion, ACG.evidenceType, Literal(kind)))
    graph.add((assertion, ACG.mappingRule, Literal(rule_id)))
    graph.add((assertion, ACG.reviewStatus, Literal('candidate_for_human_review')))
    return True


def enrich_capabilities(graph, records, selected_skills, mapping):
    rules = json.loads((ROOT / 'config/capability_mappings.json').read_text(encoding='utf-8'))
    by_entity = {}
    for r in records:
        if r['type'] not in ('Tool', 'AgentSkill'):
            continue
        descriptions = [(f['value'], source_uri(f['source']), 'curated_description_mapping')
                        for f in r['fields'] if f['field'] == 'description' and isinstance(f['value'], str)]
        kind = 'skills' if r['type'] == 'AgentSkill' else 'tools'
        name = next((f['value'] for f in r['fields'] if f['field'] == 'name'), r['id'])
        by_entity[entity_uri(r['id'])] = {'kind': kind, 'key': name if kind == 'skills' else r['id'], 'evidence': descriptions}
    for skill in selected_skills:
        original = iri('skill', skill['skill_id'])
        entity = mapping.get(original, original)
        row = by_entity.setdefault(entity, {'kind': 'skills', 'key': skill['name'], 'evidence': []})
        # Prefer the direct metadata source, but keep the matching source paired with its own text.
        row['evidence'].insert(0, (skill['description'], iri('source', skill['source_url']),
                                  'direct_skill_description_mapping' if skill.get('source_kind') == 'direct_file'
                                  else 'secondary_skill_description_mapping'))
    for entity, row in sorted(by_entity.items(), key=lambda pair: str(pair[0])):
        if any(graph.objects(entity, ACG.hasCapabilityAssertion)):
            continue  # Keep the existing 17 static-registration assertions.
        rule = rules[row['kind']].get(row['key'])
        if not rule:
            continue
        if not rule.get('evidence_pattern'):
            raise ValueError(f"Empty evidence pattern for {row['key']}")
        for evidence, source, kind in row['evidence']:
            if add_candidate(graph, entity, rule, f"{row['kind']}:{row['key']}@{rules['version']}", evidence, source, kind):
                break
    derive_servers(graph)
    write_review_queue(graph, by_entity, rules)


def derive_servers(graph):
    """A server supports a task through a tool, retaining the supporting assertion(s)."""
    for server in sorted(graph.subjects(RDF.type, ACG.MCPServer), key=str):
        support = {}
        for tool in graph.objects(server, ACG.exposesTool):
            for assertion in graph.objects(tool, ACG.hasCapabilityAssertion):
                for capability in graph.objects(assertion, ACG.assertedCapability):
                    support.setdefault(capability, set()).add(assertion)
        for capability, claims in support.items():
            derived = assertion_id(server, capability, 'derived-from-tools-v1')
            graph.add((server, ACG.hasCapabilityAssertion, derived))
            graph.add((derived, RDF.type, ACG.CapabilityAssertion))
            graph.add((derived, ACG.assertedCapability, capability))
            graph.add((derived, ACG.assertionMethod, ACG.inferred))
            graph.add((derived, ACG.evidenceType, Literal('derived_from_tool_assertions')))
            graph.add((derived, ACG.reviewStatus, Literal('candidate_for_human_review')))
            for claim in claims:
                graph.add((derived, ACG.derivedFromAssertion, claim))
                for source in graph.objects(claim, ACG.basedOnSource):
                    graph.add((derived, ACG.basedOnSource, source))


def write_review_queue(graph, descriptions, rules):
    folder = REPORTS / 'capabilities'
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'review.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['entity','name','capability','method','status','evidence_type','quote','source_urls','supporting_assertions'])
        for entity in sorted(set(graph.subjects(ACG.hasCapabilityAssertion, None)), key=str):
            for claim in sorted(graph.objects(entity, ACG.hasCapabilityAssertion), key=str):
                capability = graph.value(claim, ACG.assertedCapability)
                urls = sorted({str(url) for source in graph.objects(claim, ACG.basedOnSource)
                               for url in graph.objects(source, SCHEMA.url)})
                writer.writerow([entity, graph.value(entity, SCHEMA.name), graph.value(capability, SKOS.prefLabel),
                                 graph.value(claim, ACG.assertionMethod), graph.value(claim, ACG.reviewStatus),
                                 graph.value(claim, ACG.evidenceType), graph.value(claim, ACG.evidenceText) or '',
                                 ' ; '.join(urls), ' ; '.join(sorted(map(str, graph.objects(claim, ACG.derivedFromAssertion))))])
    with (folder / 'unclassified.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['entity','name','reason','description'])
        for entity, row in sorted(descriptions.items(), key=lambda pair: str(pair[0])):
            if any(graph.objects(entity, ACG.hasCapabilityAssertion)):
                continue
            rule = rules[row['kind']].get(row['key'])
            text = row['evidence'][0][0] if row['evidence'] else ''
            reason = 'mapping_evidence_did_not_match' if rule else 'no_task_mapping'
            if 'Replace with description' in text:
                reason = 'placeholder_description'
            writer.writerow([entity, graph.value(entity, SCHEMA.name), reason, text])
