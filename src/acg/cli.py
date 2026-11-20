"""One command for the project: build, inventory, validate, query and source updates."""
import argparse


def main():
    from . import query
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='action', required=True)
    for action in ('build', 'inventory', 'validate', 'run'):
        command = commands.add_parser(action)
        if action in ('build', 'run'):
            command.add_argument('--refresh-selection', action='store_true')
        if action in ('validate', 'run'):
            command.add_argument('--strict', action='store_true', help='Fail if a resource has no task annotation')
    query_parser = commands.add_parser('query', help='Execute a SPARQL query from queries/')
    query.add_arguments(query_parser)
    commands.add_parser('mappings', help='Refresh capability proposals from the entire database')
    commands.add_parser('database', help='Show counts for the single database and selected sample')
    import_parser = commands.add_parser('import', help='Synchronize both input sources into data/acg.sqlite3')
    import_parser.add_argument('--refresh-selection', action='store_true')
    commands.add_parser('normalize', help='Rebuild registry metadata from the existing cache, offline')
    collect_parser = commands.add_parser('collect', help='Refresh source snapshots over the network')
    collect_parser.add_argument('--source', choices=['curated', 'registry'], required=True)
    collect_parser.add_argument('--registry-pages', type=int, default=5)
    args = parser.parse_args()
    if args.action == 'mappings':
        from .capabilities import generate_mappings
        generate_mappings()
        return
    if args.action == 'database':
        import json
        from .database import export_store_report
        print(json.dumps(export_store_report(), indent=2))
        return
    if args.action == 'import':
        from .database import synchronize
        synchronize(args.refresh_selection)
        return
    if args.action == 'query':
        query.execute(args, query_parser)
        return
    if args.action in ('normalize', 'collect'):
        if args.action == 'collect' and args.source == 'curated':
            from .ingestion.curated import main as collect_curated
            collect_curated()
        else:
            from .ingestion.registry.run import main as registry
            registry(['--collect', '--registry-pages', str(args.registry_pages)] if args.action == 'collect' else [])
        from .database import synchronize
        synchronize()
        return
    if args.action in ('build', 'run'):
        from .build import build
        build(args.refresh_selection)
    if args.action in ('inventory', 'run'):
        from .inventory import inventory
        inventory()
    if args.action in ('validate', 'run'):
        from .validation import validate_project
        raise SystemExit(0 if validate_project(strict=args.strict) else 1)
