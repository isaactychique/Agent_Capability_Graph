"""Append-only rule decisions, evidence snapshots and rebuildable override output.

Hashes detect modification, not author impersonation. Legacy capture is not review.
"""
from datetime import datetime, timezone
import hashlib
import json
import re

from .paths import ROOT, REPORTS

FOLDER = ROOT/'data/curation'
HISTORY = FOLDER/'override_history.jsonl'
OUTPUT = ROOT/'config/capability_overrides.json'
SECTIONS = ('skills','tools','static_tools','entities')


def encoded(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'))


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


def replay():
    state={s:{} for s in SECTIONS};events=[];previous=None
    for line in HISTORY.read_text().splitlines():
        event=json.loads(line);event_id=event.pop('event_id')
        if event.get('previous_event')!=previous or sha(encoded(event))!=event_id:
            raise ValueError('Override history hash chain mismatch')
        if event['section'] not in SECTIONS or event['operation'] not in ('set','delete'):
            raise ValueError('Unsupported override event')
        for evidence in event['evidence']:
            if not re.fullmatch(r'[0-9a-f]{64}', evidence['text_sha256']):
                raise ValueError('Invalid evidence hash')
            path=FOLDER/'evidence'/(evidence['text_sha256']+'.txt')
            text=path.read_bytes().decode('utf-8')
            if sha(text)!=evidence['text_sha256'] or text[evidence['start']:evidence['end']]!=evidence['quote']:
                raise ValueError('Override evidence snapshot mismatch')
        section,key=event['section'],event['key']
        if event['operation']=='set':state[section][key]=event['rule']
        else:state[section].pop(key,None)
        event['event_id']=event_id;events.append(event);previous=event_id
    return state,events


def save_output(state):
    temp=OUTPUT.with_suffix('.json.part')
    def readable(value):
        if isinstance(value,list):return [readable(v) for v in value]
        if isinstance(value,dict):
            first=('action','object','evidence_pattern','source_name')
            return {k:readable(value[k]) for k in (*[k for k in first if k in value],*[k for k in value if k not in first])}
        return value
    output={section:{key:readable(rule) for key,rule in rules.items()} for section,rules in state.items()}
    temp.write_text(json.dumps(output,indent=2,ensure_ascii=False)+'\n');temp.replace(OUTPUT)


def load_overrides():
    current=json.loads(OUTPUT.read_text())
    if not HISTORY.exists():
        raise FileNotFoundError('Override history missing. Restore the versioned history/evidence; bootstrap is only for an explicit legacy migration.')
    expected,_=replay()
    if current!=expected:
        raise ValueError('Unrecorded override edits. Use pipeline.py overrides propose/record; inspect audit before rebuilding.')
    return current


def source_texts():
    """Canonical metadata descriptions with precise original source pairing."""
    from .database import connect
    with connect() as db:
        rows=db.execute('SELECT canonical_id,origin,payload_json FROM source_record ORDER BY origin,source_id').fetchall()
    for entity,origin,payload in rows:
        r=json.loads(payload)
        if origin=='curated':
            kind=r['type'];name=next((f['value'] for f in r['fields'] if f['field']=='name'),r['id'])
            for f in r['fields']:
                if f['field']=='description' and isinstance(f['value'],str) and f.get('source'):
                    yield dict(entity=entity,origin=origin,source_id=r['id'],name=name,kind=kind,
                               source_url=f['source'],revision=r.get('revision'),text=f['value'],evidence_kind='description')
        elif r.get('entity_type') in ('skill','tool') and isinstance(r.get('description'),str):
            yield dict(entity=entity,origin=origin,source_id=r.get('tool_id',r.get('skill_id')),
                       name=r['name'],kind='AgentSkill' if r['entity_type']=='skill' else 'Tool',
                       source_url=r['source_url'],revision=r.get('source_revision'),text=r['description'],
                       source_name=r.get('source_name'),evidence_kind='description')


def evidence_candidates(section,key,rule):
    if isinstance(rule,list):
        return []  # Entity lists require individually supplied, checked evidence on recording.
    result=[]
    for source in source_texts():
        eligible=(section=='skills' and source['kind']=='AgentSkill' and source['name']==key
                  or section=='tools' and source['kind']=='Tool' and source['origin']=='curated' and source['source_id']==key
                  or section=='static_tools' and source['kind']=='Tool' and source['name']==key
                     and source.get('source_name')==rule.get('source_name')
                  or section=='entities' and source['entity']==key)
        if not eligible:continue
        if rule.get('source_url') and (source['source_url']!=rule['source_url'] or source['origin']!=rule.get('origin','registry')):
            continue
        match=re.search(rule['evidence_pattern'],source['text'],re.I) if rule.get('evidence_pattern') else None
        if section!='static_tools' and match is None:continue
        text=source.pop('text')
        FOLDER.joinpath('evidence').mkdir(parents=True,exist_ok=True)
        digest=sha(text);path=FOLDER/'evidence'/(digest+'.txt')
        if not path.exists():path.write_bytes(text.encode())
        result.append(dict(source,text_sha256=digest,quote=match.group() if match else text,
                           start=match.start() if match else 0,end=match.end() if match else len(text)))
    return result


def append_event(event,previous,stream):
    event=dict(event,previous_event=previous,recorded_at=datetime.now(timezone.utc).isoformat())
    event['event_id']=sha(encoded(event))
    stream.write(encoded(event)+'\n')
    return event['event_id']


def bootstrap():
    if HISTORY.exists():
        print('Override history already exists; use audit.');return
    state=json.loads(OUTPUT.read_text())
    if set(state)!=set(SECTIONS):raise ValueError('Unexpected override sections')
    FOLDER.mkdir(parents=True,exist_ok=True)
    temp=HISTORY.with_suffix('.jsonl.part');previous=None
    try:
        with temp.open('w') as stream:
            for section in SECTIONS:
                for key,rule in state[section].items():
                    evidence=evidence_candidates(section,key,rule)
                    previous=append_event(dict(section=section,key=key,operation='set',rule=rule,
                        actor='legacy_importer',basis='legacy_snapshot_not_reviewed',
                        original_author=None,original_prompt=None,
                        rationale='Preserve existing explicit rule. Evidence matches were reconstructed now; original classification rationale is unavailable.',
                        evidence=evidence),previous,stream)
        temp.replace(HISTORY)
    except BaseException:
        if temp.exists():temp.unlink()
        raise
    audit()


def audit():
    state,events=replay();current=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else None
    latest={}
    for e in events:latest[(e['section'],e['key'])]=e
    report=dict(events=len(events),active_rules=sum(len(v) for v in state.values()),
                output_matches_history=current==state,history_head=events[-1]['event_id'] if events else None,
                active_legacy_rules=sum(e['basis']=='legacy_snapshot_not_reviewed' for (s,k),e in latest.items() if k in state[s]),
                active_rules_without_captured_evidence=sum(not e['evidence'] for (s,k),e in latest.items() if k in state[s]),
                limitations='Hashes are integrity checks, not authenticated signatures. Historical decisions remain unreviewed; semantic correctness is not established.')
    folder=REPORTS/'curation';folder.mkdir(parents=True,exist_ok=True)
    (folder/'override_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if current!=state:raise ValueError('Override output differs from recorded history')
    return report


def propose(section,key):
    state=load_overrides()
    if section not in SECTIONS or not key:raise ValueError('Unknown override section or empty key')
    rule=state[section].get(key) or {'action':'','object':'','evidence_pattern':''}
    proposal=dict(section=section,key=key,operation='set',base_rule_sha256=sha(encoded(state[section].get(key))),
                  rule=rule,actor='',rationale='',basis='source_based_revision',
                  original_author=None,original_prompt=None,evidence=evidence_candidates(section,key,rule))
    folder=FOLDER/'proposals';folder.mkdir(parents=True,exist_ok=True)
    for existing in sorted(folder.glob('*.json')):
        previous=json.loads(existing.read_text())
        if previous.get('section')==section and previous.get('key')==key and previous.get('base_rule_sha256')==proposal['base_rule_sha256']:
            print(f'Existing proposal retained: {existing.relative_to(ROOT)}. Edit and refresh it before recording.');return
    path=folder/(sha(section+'\0'+key+'\0'+proposal['base_rule_sha256'])+'.json')
    path.write_text(json.dumps(proposal,indent=2,ensure_ascii=False)+'\n')
    print(f'Proposal: {path.relative_to(ROOT)}. Fill actor and rationale; review rule and evidence before record.')


def refresh_proposal(path):
    state=load_overrides();proposal=json.loads(path.read_text())
    section,key=proposal['section'],proposal['key']
    if section not in SECTIONS:raise ValueError('Unknown override section')
    if proposal.get('base_rule_sha256')!=sha(encoded(state[section].get(key))):
        raise ValueError('Proposal base is stale; prepare a new revision')
    proposal['evidence']=evidence_candidates(section,key,proposal['rule']) if proposal['operation']=='set' else []
    path.write_text(json.dumps(proposal,indent=2,ensure_ascii=False)+'\n')
    print(f"Refreshed candidate evidence: {len(proposal['evidence'])} matches. No rule was applied.")


def provenance():
    if not HISTORY.exists():raise FileNotFoundError('Override history missing')
    state,events=replay()
    if json.loads(OUTPUT.read_text())!=state:raise ValueError('Unrecorded override edits')
    return dict(status='recorded',history_head=events[-1]['event_id'] if events else None,
                history_sha256=hashlib.sha256(HISTORY.read_bytes()).hexdigest(),
                overrides_sha256=sha(encoded(state)),historical_authorship='unknown_unless_explicitly_recorded')


def decision_index():
    if not HISTORY.exists():return {}
    _,events=replay()
    return {(e['section'],e['key']):e['event_id'] for e in events if e['operation']=='set'}


def record(path):
    state=load_overrides();_,events=replay()
    proposal=json.loads(path.read_text())
    section,key=proposal['section'],proposal['key']
    if section not in SECTIONS or not isinstance(key,str) or not key.strip():raise ValueError('Invalid rule key')
    if proposal['operation'] not in ('set','delete'):raise ValueError('Invalid operation')
    if not isinstance(proposal.get('actor'),str) or not proposal['actor'].strip() or not isinstance(proposal.get('rationale'),str) or not proposal['rationale'].strip():
        raise ValueError('Explicit actor and rationale are required')
    if proposal.get('basis') not in ('source_based_revision','human_review','documented_correction'):
        raise ValueError('Explicit decision basis is required')
    current=state[section].get(key)
    if proposal.get('base_rule_sha256')!=sha(encoded(current)):
        raise ValueError('Proposal is stale: current rule differs from its base')
    if proposal['operation']=='set':
        rule=proposal['rule'];rules=rule if isinstance(rule,list) else [rule]
        if section!='entities' and not isinstance(rule,dict):raise ValueError('Expected a rule object')
        for r in rules:
            if not all(isinstance(r.get(k),str) and r[k].strip() for k in ('action','object')):
                raise ValueError('Each rule needs nonempty action/object')
            if section=='static_tools':
                if not r.get('source_name'):raise ValueError('Static tools need source_name')
            else:
                if not r.get('evidence_pattern'):raise ValueError('Each task rule needs evidence_pattern')
                re.compile(r['evidence_pattern'])
        # Reconstruct matches against current evidence, rather than trusting proposal text.
        evidence=evidence_candidates(section,key,rule)
        if not evidence and rules:
            raise ValueError('No matching current description evidence. Body-based/entity-list decisions need an extended evidence workflow; they are not silently accepted.')
        if proposal.get('evidence')!=evidence:
            raise ValueError('Evidence changed: refresh the proposal evidence after revising its rule')
    else:evidence=[]
    event={k:proposal.get(k) for k in ('section','key','operation','rule','actor','rationale','basis','original_author','original_prompt')}
    event['evidence']=evidence
    event['base_rule_sha256']=proposal['base_rule_sha256']
    with HISTORY.open('a') as stream:append_event(event,events[-1]['event_id'] if events else None,stream)
    rebuilt,_=replay();save_output(rebuilt);audit()


def rebuild(replace=False):
    state,_=replay()
    if OUTPUT.exists() and json.loads(OUTPUT.read_text())!=state and not replace:
        raise ValueError('Unrecorded edits found. Review them before explicitly using rebuild --replace')
    save_output(state);audit()
