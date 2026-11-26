"""Evidence-backed task annotations and explicitly derived server capabilities."""
import csv
import hashlib
import json
import re

from rdflib import Literal, Namespace, RDF, URIRef

from .paths import ROOT, REPORTS
from .rdf.curated import ACG, SCHEMA, entity_uri, source_uri
from .rdf.registry import iri

SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')



def stored_descriptions():
    """Return source-paired descriptions from the complete canonical database."""
    from .database import connect
    with connect() as db:
        rows = db.execute("""SELECT s.canonical_id,s.origin,s.payload_json
            FROM source_record s JOIN entity e USING(canonical_id)
            WHERE e.kind IN ('AgentSkill','MCPTool') ORDER BY s.origin,s.source_id""").fetchall()
    for entity, origin, payload in rows:
        record = json.loads(payload)
        pairs = [(f['value'], f.get('source')) for f in record.get('fields', [])
                 if f['field'] == 'description' and isinstance(f['value'], str)] if origin == 'curated' else [
                     (record.get('description', ''), record.get('source_url'))]
        for text, url in pairs:
            if text and url:
                yield entity, origin, text, url


def generate_mappings():
    """Build a disposable artifact from vocabulary, overrides and stored evidence."""
    from .override_history import load_overrides, provenance, decision_index
    overrides = load_overrides()
    vocabulary = json.loads((ROOT / 'config/capability_vocabulary.json').read_text())
    rules = {'version': 3, **overrides, 'entities': {}, 'override_provenance': provenance()}
    for (section,key),event_id in decision_index().items():
        if section != 'entities' and key in rules.get(section,{}):
            rules[section][key]['decision_event'] = event_id
    proposals = {}
    for entity, origin, text, url in stored_descriptions():
        for concept in vocabulary['concepts']:
            for match in re.finditer(concept['pattern'], text, re.I):
                # Exclude explicit negation in the same clause before the phrase.
                prefix = re.split(r'[.;!?\n]', text[:match.start()])[-1]
                if re.search(r"\b(?:not|never|cannot|without|unsupported)\b|don't|doesn't", prefix, re.I):
                    continue
                rule = {k: concept[k] for k in ('action', 'object')}
                rule.update(evidence_pattern=re.escape(match.group()), quote=match.group(),
                            source_url=url, origin=origin, generator='description_task_v2',
                            status='candidate_for_human_review')
                proposals.setdefault(entity, {})[(rule['action'], rule['object'], url)] = rule
    from .skill_documents import documents, located_matches, fact_candidates, write_document_reports
    docs = documents()
    facts = []
    for doc in docs:
        if doc['status'] != 'available':
            continue
        for rule in located_matches(doc, vocabulary):
            proposals.setdefault(doc['entity'], {})[(rule['action'], rule['object'], doc['source_url'], rule['start'])] = rule
        for fact in fact_candidates(doc):
            candidate = dict(entity=doc['entity'], status='candidate_for_human_review', **fact)
            if candidate not in facts:
                facts.append(candidate)
    rules['body_facts'] = facts
    write_document_reports(docs, facts)
    # Canonical-entity overrides replace automatic proposals for that entity.
    rules['entities'] = {entity: list(group.values()) for entity, group in sorted(proposals.items())}
    events = decision_index()
    for entity, value in overrides.get('entities', {}).items():
        values = value if isinstance(value, list) else [value]
        for rule in values:
            if ('entities',entity) in events: rule['decision_event'] = events[('entities',entity)]
        rules['entities'][entity] = values
    rules['policy'] = ('Generated from capability_vocabulary.json, capability_overrides.json '
                       'and stored descriptions/full SKILL.md snapshots. Explicit overrides take precedence. '
                       'Automatic matches are candidates, not runtime verification.')
    path = ROOT / 'config/capability_mappings.json'
    temp = path.with_suffix('.json.part')
    temp.write_text(json.dumps(rules, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)
    print(f"Capability mappings: {sum(len(v) for v in rules['entities'].values())} entity proposals; overrides preserved")
    return rules


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
    graph.add((assertion, ACG.assertionMethod, ACG.inferred if rule.get('generator') else ACG.curatorMapped))
    graph.add((assertion, ACG.basedOnSource, source))
    graph.add((assertion, ACG.evidenceText, Literal(match.group(0))))
    graph.add((assertion, ACG.evidenceType, Literal(kind)))
    graph.add((assertion, ACG.mappingRule, Literal(rule_id)))
    if rule.get('evidence_type') == 'skill_body':
        add_location(graph, assertion, rule)
    graph.add((assertion, ACG.reviewStatus, Literal('reviewed' if rule.get('status') == 'reviewed' else 'candidate_for_human_review')))
    return True


def add_location(graph, claim, rule):
    for field, predicate in [('line','evidenceLine'), ('start','evidenceStart'),
                             ('end','evidenceEnd'), ('content_sha256','contentSha256')]:
        graph.add((claim, ACG[predicate], Literal(rule[field])))


def add_body_facts(graph, rules, docs):
    """Emit source-located candidates separately from declared dependencies."""
    for rule in rules.get('body_facts', []):
        entity = URIRef(rule['entity'])
        if (entity, RDF.type, ACG.AgentSkill) not in graph:
            continue
        doc = docs.get((rule['entity'], rule['origin'], rule['source_url']))
        if not doc or doc['content_sha256'] != rule['content_sha256']:
            continue
        if doc['text'][rule['start']:rule['end']] != rule['quote']:
            continue
        source = source_uri(rule['source_url']) if rule['origin'] == 'curated' else iri('source', rule['source_url'])
        graph.add((source, RDF.type, ACG.SourceDocument))
        graph.add((source, SCHEMA.url, URIRef(rule['source_url'])))
        if rule.get('revision'):
            graph.add((source, ACG.revision, Literal(rule['revision'])))
        claim = assertion_id(entity, rule['kind'], rule['value'], source, rule['start'])
        graph.add((entity, ACG.hasSkillFactAssertion, claim))
        graph.add((claim, RDF.type, ACG.SkillFactAssertion))
        for predicate, value in [('factKind',rule['kind']), ('factValue',rule['value']),
                                 ('evidenceText',rule['quote']), ('evidenceType','skill_body'),
                                 ('reviewStatus','candidate_for_human_review')]:
            graph.add((claim, ACG[predicate], Literal(value)))
        graph.add((claim, ACG.basedOnSource, source))
        add_location(graph, claim, rule)


def enrich_capabilities(graph, records, selected_skills, mapping):
    rules = json.loads((ROOT / 'config/capability_mappings.json').read_text(encoding='utf-8'))
    from .override_history import load_overrides
    explicit = load_overrides().get('entities', {})
    from .skill_documents import documents
    docs = {(d['entity'],d['origin'],d['source_url']):d for d in documents() if d['status']=='available'}
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
    # Use only evidence from its original source; include stored tool descriptions too.
    for entity_id, origin, text, url in stored_descriptions():
        entity = URIRef(entity_id)
        if not any(graph.triples((entity, RDF.type, None))):
            continue
        row = by_entity.setdefault(entity, {'kind': 'tools', 'key': entity_id, 'evidence': []})
        source = source_uri(url) if origin == 'curated' else iri('source', url)
        row['evidence'].append((text, source, 'stored_description_mapping'))
    for entity, row in sorted(by_entity.items(), key=lambda pair: str(pair[0])):
        manual = rules[row['kind']].get(row['key'])
        candidates = rules.get('entities', {}).get(str(entity), [])
        if manual and str(entity) not in explicit:
            candidates = [manual, *candidates]
        for rule in candidates:
            if rule.get('status') == 'rejected':
                continue
            if not rule.get('evidence_pattern'):
                raise ValueError(f"Empty evidence pattern for {row['key']}")
            evidence_rows = row['evidence']
            if rule.get('evidence_type') == 'skill_body':
                doc = docs.get((str(entity), rule['origin'], rule['source_url']))
                if (not doc or doc['content_sha256'] != rule['content_sha256']
                        or doc['text'][rule['start']:rule['end']] != rule['quote']):
                    continue
                source = source_uri(rule['source_url']) if rule['origin'] == 'curated' else iri('source', rule['source_url'])
                graph.add((source, RDF.type, ACG.SourceDocument))
                graph.add((source, SCHEMA.url, URIRef(rule['source_url'])))
                if rule.get('revision'):
                    graph.add((source, ACG.revision, Literal(rule['revision'])))
                evidence_rows = [(rule['quote'], source, 'skill_body')]
            for evidence, source, kind in evidence_rows:
                if rule.get('source_url'):
                    expected = source_uri(rule['source_url']) if rule.get('origin') == 'curated' else iri('source', rule['source_url'])
                    if source != expected:
                        continue
                capability = iri('capability', f"{rule['action']}/{rule['object']}")
                if any(graph.value(claim, ACG.assertedCapability) == capability
                       for claim in graph.objects(entity, ACG.hasCapabilityAssertion)):
                    continue
                if add_candidate(graph, entity, rule, f"{row['kind']}:{row['key']}@{rules['version']}", evidence, source, kind):
                    break
    add_body_facts(graph, rules, docs)
    from .llm_extraction import apply_results
    apply_results(graph)
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
        writer.writerow(['entity','name','capability','method','status','evidence_type','quote','source_urls','supporting_assertions','line','start','end','content_sha256'])
        for entity in sorted(set(graph.subjects(ACG.hasCapabilityAssertion, None)), key=str):
            for claim in sorted(graph.objects(entity, ACG.hasCapabilityAssertion), key=str):
                capability = graph.value(claim, ACG.assertedCapability)
                urls = sorted({str(url) for source in graph.objects(claim, ACG.basedOnSource)
                               for url in graph.objects(source, SCHEMA.url)})
                writer.writerow([entity, graph.value(entity, SCHEMA.name), graph.value(capability, SKOS.prefLabel),
                                 graph.value(claim, ACG.assertionMethod), graph.value(claim, ACG.reviewStatus),
                                 graph.value(claim, ACG.evidenceType), graph.value(claim, ACG.evidenceText) or '',
                                 ' ; '.join(urls), ' ; '.join(sorted(map(str, graph.objects(claim, ACG.derivedFromAssertion)))),
                                 graph.value(claim, ACG.evidenceLine) or '',
                                 graph.value(claim, ACG.evidenceStart) if graph.value(claim, ACG.evidenceStart) is not None else '',
                                 graph.value(claim, ACG.evidenceEnd) or '', graph.value(claim, ACG.contentSha256) or ''])
    with (folder / 'unclassified.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream, lineterminator='\n')
        writer.writerow(['entity','name','reason','description'])
        for entity, row in sorted(descriptions.items(), key=lambda pair: str(pair[0])):
            if any(graph.objects(entity, ACG.hasCapabilityAssertion)):
                continue
            rule = rules[row['kind']].get(row['key']) or rules.get('entities', {}).get(str(entity))
            text = row['evidence'][0][0] if row['evidence'] else ''
            reason = 'mapping_evidence_did_not_match' if rule else 'no_task_mapping'
            if 'Replace with description' in text:
                reason = 'placeholder_description'
            writer.writerow([entity, graph.value(entity, SCHEMA.name), reason, text])
