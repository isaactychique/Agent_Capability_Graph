"""Offline prompt contract; does not call an endpoint or alter capability mappings."""
import argparse
import hashlib
import json
import re
from pathlib import Path
from rdflib import Graph, Namespace, RDF, Literal
SKOS=Namespace('http://www.w3.org/2004/02/skos/core#')

def load_vocabulary(path):
    g=Graph().parse(path); schemes=set(g.subjects(RDF.type,SKOS.ConceptScheme))
    if len(schemes)!=1: raise ValueError('Expected one ConceptScheme')
    scheme=next(iter(schemes)); concepts=[]
    for c in sorted(set(g.subjects(SKOS.inScheme,scheme)),key=str):
        if (c,RDF.type,SKOS.Concept) not in g: raise ValueError('Concept must be typed skos:Concept')
        if not str(c).startswith('https://'): raise ValueError('Expected proposed HTTPS concept identifiers')
        labels=list(g.objects(c,SKOS.prefLabel)); definitions=list(g.objects(c,SKOS.definition))
        if not labels or not definitions or any(not isinstance(v, Literal) or not str(v).strip() for v in labels + definitions): raise ValueError('Each concept needs nonempty literal labels and definitions')
        concepts.append({'uri':str(c),'labels':[str(x) for x in labels],'definitions':[str(x) for x in definitions],'scope_notes':[str(x) for x in g.objects(c,SKOS.scopeNote)]})
    if not 15<=len(concepts)<=25: raise ValueError('Await Isaac fixed vocabulary: expected 15-25 concepts')
    return {'version':hashlib.sha256(path.read_bytes()).hexdigest(),'scheme':str(scheme),'concepts':concepts}

def render(vocabulary,resource):
    if not isinstance(resource.get('resource_id'),str) or not isinstance(resource.get('description'),str): raise ValueError('resource_id and description required')
    template=(Path(__file__).resolve().parents[2]/'prompts/capability_extraction_v1.txt').read_text()
    payloads = {'VOCABULARY_JSON': vocabulary, 'RESOURCE_JSON': resource}
    # Substitute only markers in the template, never marker-like text in source data.
    return re.sub(r'{{(VOCABULARY_JSON|RESOURCE_JSON)}}', lambda m: json.dumps(payloads[m.group(1)], ensure_ascii=False), template)

def validate_response(response,vocabulary,resource):
    keys={'resource_id','vocabulary_version','status','assignments','suggestions','reason'}
    if not isinstance(response,dict) or set(response)!=keys: raise ValueError('Invalid response keys')
    if response['resource_id']!=resource['resource_id'] or response['vocabulary_version']!=vocabulary['version']: raise ValueError('Identity/version mismatch')
    if not isinstance(response['status'], str) or response['status'] not in {'classified','unclassified','out_of_scope'}: raise ValueError('Invalid status')
    if not isinstance(response['reason'],str) or not response['reason'].strip(): raise ValueError('Reason required')
    allowed={c['uri'] for c in vocabulary['concepts']}; seen=set()
    for key,required in [('assignments',{'concept_uri','evidence'}),('suggestions',{'label','definition','evidence'})]:
        if not isinstance(response[key],list): raise ValueError('Expected list')
        for item in response[key]:
            if not isinstance(item,dict) or set(item)!=required or not all(isinstance(v,str) and v.strip() for v in item.values()): raise ValueError('Invalid item')
            if item['evidence'] not in resource['description']: raise ValueError('Evidence is not exact source substring')
            if key=='assignments':
                if item['concept_uri'] not in allowed or item['concept_uri'] in seen: raise ValueError('Unknown or duplicate concept')
                seen.add(item['concept_uri'])
    if (response['status']=='classified') != bool(response['assignments']): raise ValueError('Status/assignments disagree')
    return response

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--vocabulary',type=Path,required=True);p.add_argument('--resource',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();v=load_vocabulary(a.vocabulary);r=json.loads(a.resource.read_text());a.output.write_text(render(v,r))
