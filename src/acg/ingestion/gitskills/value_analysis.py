"""Value analysis of the pinned corpus, preserving existing baseline outputs."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone
import duckdb
from .parser import parse_content, value_type, PARSER_VERSION
from .collect import REVISION
FIELDS = ('version','allowed-tools','tags','argument-hint','author','user-invocable','compatibility','category','disable-model-invocation','model','context','license')

def groups(field, value):
    """Syntactic/lexical groups, not semantic classifications. May overlap."""
    kind=value_type(value)
    if value is None or value == '' or value == [] or value == {}: return ['empty']
    if field in ('user-invocable','disable-model-invocation'):
        return [str(value).lower() if kind=='boolean' else 'non_boolean:'+kind]
    if field=='version':
        if kind=='number': return ['numeric_yaml']
        if kind!='string': return ['other:'+kind]
        if re.fullmatch(r'v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?',value.strip()): return ['three_part_version_like']
        if re.fullmatch(r'v?\d+(?:\.\d+)?',value.strip()): return ['one_or_two_part_version_like']
        return ['other_string']
    if field in ('tags','category','model','context'):
        vals=value if kind=='list' else [value]
        return sorted({v.strip().casefold() for v in vals if isinstance(v,str) and v.strip()}) or ['non_string_or_empty_items']
    if field in ('allowed-tools','compatibility'):
        if field=='compatibility' and kind!='string': return ['other:'+kind]
        if kind not in ('string','list'): return ['other:'+kind]
        s=str(value).lower()
        rules=({'shell':r'\b(bash|shell|terminal)\b','file_read':r'\b(read|glob|grep)\b','file_write':r'\b(write|edit|multiedit)\b','web':r'\b(webfetch|websearch|fetch)\b','mcp_reference':r'\bmcp[_:]'} if field=='allowed-tools' else {'claude':'claude','codex':'codex','python':'python','node_js':r'node|npm|javascript','network':r'internet|network|https?://','os_constraint':r'linux|macos|windows|darwin','docker':'docker','git':r'\bgit\b'})
        return [k for k,p in rules.items() if re.search(p,s)] or ['other_text']
    if field=='argument-hint': return ['placeholder_syntax' if isinstance(value,str) and re.search(r'\[|<|\$',value) else 'other:'+kind]
    if field=='author': return [('url_like' if re.match(r'https?://',value) else 'handle_like' if value.startswith('@') else 'name_or_free_text') if kind=='string' else 'structured:'+kind]
    return [kind]

def write_csv(path, header, rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f,lineterminator='\n'); w.writerow(header); w.writerows(rows)

def run(cache,out):
    manifest=json.loads((cache/'manifest.json').read_text())
    if manifest['revision']!=REVISION or not manifest.get('verified_at'): raise ValueError('Unverified/wrong cache')
    for f in manifest['files']:
        if (cache/f['path']).stat().st_size!=f['size']: raise ValueError('Cache size mismatch')
    out.mkdir(parents=True,exist_ok=True)
    d=duckdb.connect(); d.execute("SET memory_limit='1GB'"); d.execute('SET threads=2')
    counts=Counter(); types=Counter(); gc=Counter(); vals=defaultdict(Counter); examples={}; statuses=Counter()
    for part in sorted(cache.glob('data/artifacts/*.parquet')):
        cur=d.cursor().execute('SELECT file_sha, repo_full_name, path, content, content_fetched FROM read_parquet(?) WHERE dedup_primary=1',[str(part)])
        while batch:=cur.fetchmany(256):
            for sha,repo,path,content,fetched in batch:
                status,meta,_=parse_content(content,sha,fetched); statuses[status]+=1
                if status!='parsed': continue
                for scope,mapping in [('top',meta),('metadata',meta.get('metadata',{}))]:
                    if not isinstance(mapping,dict): continue
                    for field in FIELDS:
                        if field not in mapping: continue
                        value=mapping[field]; key=(scope,field); counts[key]+=1; types[(*key,value_type(value))]+=1
                        try: literal=json.dumps(value,ensure_ascii=False,sort_keys=True,default=str)
                        except (ValueError,TypeError,RecursionError): literal='<non-JSON-YAML-value>'
                        vals[key][literal]+=1
                        for group in groups(field,value):
                            g=(*key,group); gc[g]+=1
                            if g not in examples: examples[g]=(sha,repo,path,literal)
        cur.close(); print(part.name,sum(statuses.values()),flush=True)
    baseline=Path(__file__).resolve().parents[4]/'reports/gitskills'
    expected={r['parse_status']:int(r['unique_contents']) for r in csv.DictReader((baseline/'parse_status.csv').open())}
    if dict(statuses)!=expected: raise AssertionError('Parser totals differ from baseline')
    expected_types={(r['scope'],r['field'],r['value_type']):int(r['unique_contents']) for r in csv.DictReader((baseline/'frontmatter_fields.csv').open()) if r['field'] in FIELDS}
    if dict(types)!=expected_types: raise AssertionError('Field/type totals differ from baseline')
    den=statuses['parsed']
    write_csv(out/'field_summary.csv',['scope','field','present_contents','parsed_denominator','pct_parsed','distinct_serialized_values'],[(*k,n,den,round(n/den*100,5),len(vals[k])) for k,n in sorted(counts.items())])
    write_csv(out/'value_types.csv',['scope','field','type','contents'],[(*k,n) for k,n in sorted(types.items())])
    write_csv(out/'value_groups.csv',['scope','field','group','contents','field_present_denominator','pct_field_present'],[(*k,n,counts[k[:2]],round(n/counts[k[:2]]*100,5)) for k,n in sorted(gc.items())])
    write_csv(out/'top_values.csv',['scope','field','value_json','contents','field_present_denominator'],[(*k,v,n,counts[k]) for k,c in sorted(vals.items()) for v,n in sorted(c.items(),key=lambda x:(-x[1],x[0]))[:20]])
    rows=[]
    for key in sorted(counts):
        keys=sorted([k for k in gc if k[:2]==key],key=lambda k:(-gc[k],k))[:10]
        for k in keys:
            sha,repo,path,value=examples[k]; rows.append((*k,gc[k],sha,repo,path,value[:1000],len(value)>1000,f'https://api.github.com/repos/{repo}/git/blobs/{sha}'))
    write_csv(out/'examples.csv',['scope','field','group','group_contents','file_sha','repository','path','value_excerpt','truncated','blob_url'],rows)
    result={'dataset_revision':REVISION,'parser_version':PARSER_VERSION,'completed_at':datetime.now(timezone.utc).isoformat(),'unit':'one representative per exact Git blob hash; top and metadata scopes separate','fields':FIELDS,'parse_status':dict(statuses),'baseline_field_type_reconciliation':True,'grouping':'deterministic lexical rules; multi-label groups overlap; not semantic truth','script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'source_files':manifest['files']}
    (out/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--cache',type=Path,required=True); p.add_argument('--output',type=Path,required=True); a=p.parse_args(); run(a.cache,a.output)
