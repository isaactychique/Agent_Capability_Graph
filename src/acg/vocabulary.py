"""Fixed SKOS vocabulary and auditable legacy-to-v1 clustering proposals."""
import csv
import hashlib
import json
import re
from rdflib import Graph, Namespace, RDF
from .paths import ROOT, GRAPH, REPORTS

SKOS = Namespace('http://www.w3.org/2004/02/skos/core#')
ACG = Namespace('urn:acg:ontology:')


def concepts():
    path = ROOT / 'ontology/capabilities_v1.ttl'
    graph = Graph().parse(path)
    result = [{'id':str(graph.value(c,SKOS.notation)), 'uri':str(c),
               'label':str(graph.value(c,SKOS.prefLabel)),
               'definition':str(graph.value(c,SKOS.definition)),
               'scope':str(graph.value(c,SKOS.scopeNote))}
              for c in graph.subjects(RDF.type,SKOS.Concept)]
    if not 15 <= len(result) <= 25 or len({c['id'] for c in result}) != len(result):
        raise ValueError('Expected 15–25 distinct vocabulary concepts')
    return sorted(result,key=lambda c:c['id'])


def cluster_capabilities():
    valid = {c['id'] for c in concepts()}
    config = json.loads((ROOT/'config/capability_clusters_v1.json').read_text())
    if any(r['concept_id'] not in valid for r in config['rules']):
        raise ValueError('Cluster rule references an unknown concept')
    graph = Graph().parse(GRAPH)
    rows = []
    for cap in sorted(graph.subjects(RDF.type,ACG.Capability),key=str):
        label = str(graph.value(cap,SKOS.prefLabel))
        matches = [r['concept_id'] for r in config['rules'] if re.search(r['pattern'],label,re.I)]
        rows.append(dict(capability_uri=cap,label=label,proposed_concepts=' ; '.join(matches),
                         status='unresolved' if not matches else 'ambiguous' if len(matches)>1 else 'candidate',
                         decision='pending'))
    folder=REPORTS/'vocabulary'; folder.mkdir(parents=True,exist_ok=True)
    with (folder/'legacy_clusters.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['capability_uri','label','proposed_concepts','status','decision'])
        writer.writeheader();writer.writerows(rows)
    from collections import Counter
    summary=dict(vocabulary_concepts=len(valid),observed_legacy_concepts=len(rows),
                 graph_sha256=hashlib.sha256(GRAPH.read_bytes()).hexdigest(),
                 statuses=dict(Counter(r['status'] for r in rows)),review_status='pending')
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2))
