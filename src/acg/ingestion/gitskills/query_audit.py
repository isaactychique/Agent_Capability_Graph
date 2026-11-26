"""Execute Lin's CQ11-20 against a fixed graph; export evidence, not accuracy claims."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from rdflib import Graph, Namespace, RDF

def run(root,output):
    graph_path=root/'data/processed/agent_capability_graph.ttl'; g=Graph().parse(graph_path)
    output.mkdir(parents=True,exist_ok=True); a=Namespace('urn:acg:ontology:')
    report={'graph_sha256':hashlib.sha256(graph_path.read_bytes()).hexdigest(),'triples':len(g),'entities':{t:len(set(g.subjects(RDF.type,a[t]))) for t in ['MCPServer','MCPTool','AgentSkill','Capability','CapabilityAssertion']},'queries':[]}
    for rec in json.loads((root/'docs/lin_docs /lin_queries.json').read_text()):
        path=root/rec['query']; result=g.query(path.read_text()); columns=[str(v) for v in result.vars]; rows=list(result)
        with (output/(rec['id']+'.csv')).open('w',newline='') as f:
            w=csv.writer(f,lineterminator='\n');w.writerow(columns);w.writerows(['' if v is None else str(v) for v in row] for row in rows)
        bound=sum('value' in row.asdict() for row in rows) if 'value' in columns else None
        report['queries'].append({'id':rec['id'],'rows':len(rows),'rows_with_value':bound,'distinct_skills':len({row.asdict()['skill'] for row in rows if 'skill' in row.asdict()}) if 'skill' in columns else None,'rows_with_field_source':sum('source' in row.asdict() for row in rows) if 'source' in columns else None,'query_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'status':'executed','interpretation':'No match in this snapshot; not evidence of real-world absence' if not rows else 'Recorded observations/projections; inspect representation and missing field-level provenance; no semantic accuracy claim'})
    (output/'query_audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.cwd());p.add_argument('--output',type=Path,default=Path('reports/nov26'));a=p.parse_args();run(a.root,a.output)
