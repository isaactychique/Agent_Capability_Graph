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
    parser.add_argument("--format", help="Format parameter for skills_by_format.rq")
    parser.add_argument("--name", help="Entity name for entity_capabilities.rq")


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
            parser.error("--format is required for skills_by_format.rq")
        escaped_format = args.format.replace('\\', '\\\\').replace('"', '\\"')
        query = query.replace("__FORMAT__", escaped_format)
    if "__NAME__" in query:
        if not args.name:
            parser.error("--name is required for entity_capabilities.rq")
        query = query.replace("__NAME__", Literal(args.name).n3())
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
