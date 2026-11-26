"""Explicit, auditable closed-vocabulary extraction step (OpenAI-chat adapter)."""
import hashlib
import json
import os
from pathlib import Path
from .paths import ROOT, REPORTS
from .vocabulary import concepts

FOLDER = REPORTS/'llm'
JOBS = FOLDER/'requests.jsonl'
RESULTS = FOLDER/'validated.jsonl'


def digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def prepare(limit=None):
    from .database import connect
    from .skill_documents import documents
    from .capabilities import stored_descriptions
    prompt=(ROOT/'prompts/capability_extraction_v1.txt').read_text()
    vocabulary=concepts()
    with connect() as db:
        entities=[r[0] for r in db.execute("SELECT canonical_id FROM entity WHERE kind='AgentSkill' AND in_sample=1 ORDER BY canonical_id")]
    if limit is not None:
        if limit<1:raise ValueError('limit must be positive')
        entities=entities[:limit]
    candidates={}
    for d in documents():
        if d['status']=='available':candidates.setdefault(d['entity'],d)
    for entity,origin,text,url in stored_descriptions():
        candidates.setdefault(entity,dict(entity=entity,origin=origin,text=text,source_url=url,
                                          revision=None,content_sha256=digest(text),evidence_type='description'))
    jobs=[]
    for entity in entities:
        d=candidates.get(entity)
        if not d:continue
        for start in range(0,len(d['text']),8000):
            data=dict(entity=entity,source_url=d['source_url'],origin=d['origin'],
                      content_sha256=d['content_sha256'],revision=d.get('revision'),
                      evidence_type=d.get('evidence_type','skill_body'),chunk_offset=start,
                      text=d['text'][start:start+8000],allowed_concepts=vocabulary)
            messages=[{'role':'system','content':prompt},{'role':'user','content':json.dumps(data,ensure_ascii=False)}]
            jobs.append(dict(job_id=digest(json.dumps(messages,ensure_ascii=False)),input=data,messages=messages))
    FOLDER.mkdir(parents=True,exist_ok=True)
    temp=JOBS.with_suffix('.jsonl.part')
    temp.write_text(''.join(json.dumps(j,ensure_ascii=False)+'\n' for j in jobs));temp.replace(JOBS)
    print(f'Prepared {len(jobs)} requests for {len(entities)} selected Skills; no endpoint contacted.')
    return jobs


def validate_response(job, value):
    allowed={c['id'] for c in job['input']['allowed_concepts']}
    if not isinstance(value,dict) or set(value)!={'selected','suggestions','abstention_reason'}:
        raise ValueError('Unexpected JSON response keys')
    if not isinstance(value['selected'],list) or len(value['selected'])>5 or not isinstance(value['suggestions'],list) or not isinstance(value['abstention_reason'],str):
        raise ValueError('Invalid response types')
    seen=set();data=job['input'];begin=data['chunk_offset'];text=data['text']
    for r in value['selected']:
        if not isinstance(r,dict) or set(r)!={'concept_id','quote','start','end'}:
            raise ValueError('Invalid selection schema')
        if r['concept_id'] not in allowed or r['concept_id'] in seen:
            raise ValueError('Unknown or repeated concept ID')
        seen.add(r['concept_id'])
        if type(r['start']) is not int or type(r['end']) is not int or not isinstance(r['quote'],str) or not r['quote']:
            raise ValueError('Invalid quote or offsets')
        if not begin<=r['start']<r['end']<=begin+len(text) or text[r['start']-begin:r['end']-begin]!=r['quote']:
            raise ValueError('Quote does not match source chunk offsets')
    for r in value['suggestions']:
        if not isinstance(r,dict) or set(r)!={'label','rationale','quote'} or not all(isinstance(v,str) and v for v in r.values()) or r['quote'] not in text:
            raise ValueError('Invalid suggestion or missing evidence')
    return value


def extract(api_format):
    if api_format!='openai-chat':raise ValueError('Only the explicit openai-chat adapter is implemented')
    endpoint=os.environ.get('ACG_LLM_ENDPOINT'); model=os.environ.get('ACG_LLM_MODEL')
    if not endpoint or not model:raise ValueError('Set ACG_LLM_ENDPOINT (full chat-completions URL) and ACG_LLM_MODEL')
    if not endpoint.startswith('https://'):raise ValueError('The remote endpoint must use HTTPS')
    if not JOBS.exists():raise ValueError('Run extract-capabilities --prepare first')
    from urllib.request import Request,urlopen
    from datetime import datetime,timezone
    run_id=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run_folder=FOLDER/'runs'/run_id;run_folder.mkdir(parents=True,exist_ok=True)
    (run_folder/'requests.jsonl').write_bytes(JOBS.read_bytes())
    results=[];errors=[];raw_responses=[]
    for line in JOBS.read_text().splitlines():
        job=json.loads(line)
        try:
            headers={'Content-Type':'application/json'}
            key=os.environ.get('ACG_LLM_API_KEY')
            if key:headers['Authorization']='Bearer '+key
            body=json.dumps(dict(model=model,messages=job['messages'],temperature=0)).encode()
            with urlopen(Request(endpoint,data=body,headers=headers),timeout=90) as response:
                raw=json.loads(response.read(2_000_000))
            raw_responses.append(dict(job_id=job['job_id'],response=raw))
            content=raw['choices'][0]['message']['content']
            value=validate_response(job,json.loads(content))
            results.append(dict(job_id=job['job_id'],input=job['input'],response=value,
                                model=model,created_at=datetime.now(timezone.utc).isoformat(),status='candidate_for_human_review'))
        except Exception as exc:
            # Avoid emitting request headers, secret values or unreviewed model text.
            errors.append(dict(job_id=job['job_id'],error_type=type(exc).__name__))
        print(f"LLM requests: {len(results)+len(errors)} processed; {len(errors)} rejected",flush=True)
    temp=RESULTS.with_suffix('.jsonl.part')
    temp.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in results));temp.replace(RESULTS)
    (FOLDER/'errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    (run_folder/'validated.jsonl').write_bytes(RESULTS.read_bytes())
    (run_folder/'raw_responses.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in raw_responses))
    (run_folder/'errors.json').write_text(json.dumps(errors,indent=2)+'\n')
    # Suggestions stay in validated artifacts for manual review, never applied.
    print(f'Validated responses: {len(results)}; rejected/failed: {len(errors)}')
    if errors:raise RuntimeError('Some requests failed; inspect reports/llm/errors.json')


def apply_results(graph):
    """Apply saved responses only when their vocabulary and current evidence still match."""
    if not RESULTS.exists():
        return
    from rdflib import Literal,RDF,URIRef
    from .skill_documents import documents
    from .capabilities import stored_descriptions,assertion_id,ACG,SCHEMA,source_uri,iri,add_location
    vocabulary=concepts(); allowed={c['id']:c for c in vocabulary}
    sources={}
    for d in documents():
        if d['status']=='available':sources[(d['entity'],d['origin'],d['source_url'],d['content_sha256'])]=d['text']
    for entity,origin,text,url in stored_descriptions():
        sources[(entity,origin,url,digest(text))]=text
    rows=[json.loads(line) for line in RESULTS.read_text().splitlines() if line.strip()]
    # Validate the whole artifact before emitting any assertions.
    accepted=[]
    for row in rows:
        data=row['input']
        messages=[{'role':'system','content':(ROOT/'prompts/capability_extraction_v1.txt').read_text()},
                  {'role':'user','content':json.dumps(data,ensure_ascii=False)}]
        if row['job_id']!=digest(json.dumps(messages,ensure_ascii=False)):
            raise ValueError('LLM prompt or request identity changed')
        if data['allowed_concepts']!=vocabulary:
            raise ValueError('LLM vocabulary changed; regenerate requests and results')
        validate_response({'input':data},row['response'])
        text=sources.get((data['entity'],data['origin'],data['source_url'],data['content_sha256']))
        if text is None:
            raise ValueError('LLM source snapshot no longer matches SQLite')
        if text[data['chunk_offset']:data['chunk_offset']+len(data['text'])]!=data['text']:
            raise ValueError('LLM chunk no longer matches stored source')
        accepted.append((row,text))
    graph+=graph_vocabulary()
    for row,text in accepted:
        data=row['input'];entity=URIRef(data['entity'])
        if (entity,RDF.type,ACG.AgentSkill) not in graph:continue
        source=source_uri(data['source_url']) if data['origin']=='curated' else iri('source',data['source_url'])
        graph.add((source,RDF.type,ACG.SourceDocument));graph.add((source,SCHEMA.url,URIRef(data['source_url'])))
        if data.get('revision'):graph.add((source,ACG.revision,Literal(data['revision'])))
        for selection in row['response']['selected']:
            concept=allowed[selection['concept_id']];cap=URIRef(concept['uri'])
            graph.add((cap,RDF.type,ACG.Capability))
            graph.add((cap,ACG.capabilityAction,Literal('perform')))
            graph.add((cap,ACG.capabilityObject,Literal(concept['label'])))
            claim=assertion_id('llm-v1',row['job_id'],selection['concept_id'])
            graph.add((entity,ACG.hasCapabilityAssertion,claim));graph.add((claim,RDF.type,ACG.CapabilityAssertion))
            graph.add((claim,ACG.assertedCapability,cap));graph.add((claim,ACG.basedOnSource,source))
            for predicate,value in [('evidenceText',selection['quote']),('evidenceType','llm_fixed_vocabulary'),
                                    ('reviewStatus','candidate_for_human_review'),('llmModel',row['model']),
                                    ('mappingRule','fixed-skos-v1:'+row['job_id'])]:
                graph.add((claim,ACG[predicate],Literal(value)))
            graph.add((claim,ACG.assertionMethod,ACG.inferred))
            located=dict(selection,content_sha256=data['content_sha256'],line=text[:selection['start']].count('\n')+1)
            add_location(graph,claim,located)


def graph_vocabulary():
    from rdflib import Graph
    return Graph().parse(ROOT/'ontology/capabilities_v1.ttl')
