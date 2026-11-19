"""Validate RDF structure and report annotation coverage independently."""
import argparse
from pathlib import Path

from pyshacl import validate
from rdflib import Graph, Namespace, RDF

from .paths import GRAPH, SHAPES, COVERAGE_SHAPES, REPORTS

ACG = Namespace('urn:acg:ontology:')
SH = Namespace('http://www.w3.org/ns/shacl#')


def save_report(folder, name, report, text):
    folder.mkdir(parents=True, exist_ok=True)
    report.serialize(destination=folder / f'{name}.ttl', format='turtle')
    (folder / f'{name}.txt').write_text(text, encoding='utf-8')


def validate_file(graph_path, output_dir, strict=False):
    graph = Graph().parse(graph_path, format='turtle')
    if not any(graph.subjects(RDF.type, ACG.MCPServer)):
        raise ValueError('No MCPServer: refusing an empty or unrelated corpus')
    conforms, report, text = validate(graph, shacl_graph=str(SHAPES), inference='none', meta_shacl=True)
    save_report(output_dir, 'report', report, text)
    covered, quality_report, quality_text = validate(
        graph, shacl_graph=str(COVERAGE_SHAPES), inference='none', meta_shacl=True,
    )
    save_report(output_dir, 'coverage', quality_report, quality_text)
    missing = len(set(quality_report.objects(None, SH.focusNode)))
    print(f'Structure SHACL: {"PASS" if conforms else "FAIL"}')
    print(f'Task annotation coverage SHACL: {"PASS" if covered else str(missing) + " resource(s) unclassified"}')
    print(f'Reports: {output_dir}')
    print('A structural PASS does not mean that capability annotations are reviewed or complete.')
    return bool(conforms) and (bool(covered) if strict else True)


def validate_project(strict=False):
    return validate_file(GRAPH, REPORTS / 'validation/unified', strict)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('graph', type=Path, nargs='?', default=GRAPH)
    parser.add_argument('--output', type=Path, default=REPORTS / 'validation/unified')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    raise SystemExit(0 if validate_file(args.graph, args.output, args.strict) else 1)


if __name__ == '__main__':
    main()
