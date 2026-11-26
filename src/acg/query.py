#!/usr/bin/env python3
"""Run a SPARQL SELECT query against the unified RDF graph."""

import argparse
from pathlib import Path

from rdflib import Graph, Literal


from acg.paths import ROOT as PROJECT_ROOT, GRAPH
QUERY_DIR = PROJECT_ROOT / "queries"


def add_arguments(parser):
    parser.add_argument(
        "query",
        type=Path,
        help="SPARQL query filename in this folder or direct path to a .rq file",
    )
    parser.add_argument("--graph", type=Path, default=GRAPH)
    parser.add_argument("--dataset", choices=["unified"], default="unified", help=argparse.SUPPRESS)
    parser.add_argument("--format", help="Format parameter for queries using __FORMAT__")
    parser.add_argument("--action", dest="task_action", help="Action filter for tools_by_action.rq")
    parser.add_argument("--bundle", choices=["scripts", "references", "assets"], help="Bundle kind for CQ16")
    parser.add_argument("--name", help="Entity name for queries using __NAME__")


def execute(args, parser):
    query_path = args.query if args.query.is_file() else QUERY_DIR / args.query
    if not query_path.is_file():
        parser.error(f"SPARQL query not found: {args.query} (looked in {QUERY_DIR})")
    graph = Graph()
    graph_path = args.graph
    graph.parse(graph_path, format="turtle")
    query = query_path.read_text(encoding="utf-8")
    if "__FORMAT__" in query:
        if not args.format:
            parser.error("--format is required for this query")
        escaped_format = args.format.replace('\\', '\\\\').replace('"', '\\"')
        query = query.replace("__FORMAT__", escaped_format)
    if "__NAME__" in query:
        if not args.name:
            parser.error("--name is required for this query")
        query = query.replace("__NAME__", Literal(args.name).n3())
    if "__ACTION__" in query:
        if not args.task_action:
            parser.error("--action is required for this query")
        query = query.replace("__ACTION__", Literal(args.task_action).n3())
    if "__BUNDLE__" in query:
        if not args.bundle:
            parser.error("--bundle is required for this query")
        query = query.replace("__BUNDLE__", Literal(args.bundle).n3())
    result = graph.query(query)
    columns = [str(v) for v in result.vars]
    print(" | ".join(columns))
    print(" | ".join("---" for _ in columns))
    for row in result:
        print(" | ".join(str(value) if value is not None else "" for value in row))
    print(f"\n{len(result)} result(s)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    add_arguments(parser)
    execute(parser.parse_args(argv), parser)


if __name__ == "__main__":
    main()



def competency_report():
    """Execute the atomic competency catalogue and record result counts."""
    import csv, json
    from .paths import REPORTS
    cases = [
        ('CQ01','cq01_web_search',{}),
        ('CQ02','cq02_skill_formats',{'__FORMAT__':'PDF'}),
        ('CQ02','cq02_skill_formats',{'__FORMAT__':'spreadsheet'}),
        ('CQ03','cq03_skill_dependencies',{'__NAME__':'phoenix-observability'}),
        ('CQ04','cq04_resource_capabilities',{'__NAME__':'pdf'}),
        ('CQ05','cq05_tools_by_action',{'__ACTION__':'search'}),
        ('CQ06','cq06_assertion_evidence',{'__NAME__':'pdf'}),
        ('CQ07','cq07_tool_inputs',{}),
        ('CQ07b','cq07b_tool_required_parameters',{}),
        ('CQ08','cq08_tool_outputs',{}),
        ('CQ09','cq09_server_resources',{}),
        ('CQ10','cq10_server_prompts',{}),
        ('CQ11','cq11_licenses',{}),
        ('CQ12','cq12_permissions',{}),
        ('CQ12b','cq12b_skill_allowed_tools',{}),
        ('CQ13','cq13_security_signals',{}),
        ('CQ14','cq14_server_transports',{}),
        ('CQ15','cq15_versions',{}),
        *[('CQ16','cq16_skill_bundles',{'__BUNDLE__':kind})
          for kind in ('scripts','references','assets')],
        ('CQ17','cq17_repositories',{}),
        ('CQ18','cq18_compatibility',{}),
        ('CQ19','cq19_unclassified',{}),
        ('CQ20','cq20_review_status',{})]
    graph=Graph().parse(GRAPH);rows=[]
    for cid,name,params in cases:
        query=(QUERY_DIR/(name+'.rq')).read_text()
        for key,value in params.items():
            # __FORMAT__ is inside an existing quoted string; __NAME__ is a term.
            query=query.replace(key, value if key=='__FORMAT__' else Literal(value).n3())
        try:
            count=len(list(graph.query(query)));status='executed';error=''
        except Exception as exc:
            count='';status='error';error=type(exc).__name__
        rows.append(dict(cq=cid,query=name+'.rq',parameters=json.dumps(params),rows=count,status=status,error=error))
    folder=REPORTS/'queries';folder.mkdir(parents=True,exist_ok=True)
    with (folder/'competency_coverage.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['cq','query','parameters','rows','status','error'])
        writer.writeheader();writer.writerows(rows)
    print(f"Competency formulations: {len({r['cq'] for r in rows})}; executions: {len(rows)}; errors: {sum(r['status']=='error' for r in rows)}")
    if any(r['status']=='error' for r in rows):raise RuntimeError('Some competency queries failed')
