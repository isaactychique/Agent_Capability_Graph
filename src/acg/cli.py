"""One command for the project: build, inventory, validate, query and source updates."""
import argparse
from pathlib import Path


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
    override_parser = commands.add_parser('overrides', help='Trace, audit and reconstruct explicit capability rules')
    override_parser.add_argument('operation', choices=['bootstrap','audit','propose','refresh','record','rebuild'])
    override_parser.add_argument('--section', choices=['skills','tools','static_tools','entities'])
    override_parser.add_argument('--key')
    override_parser.add_argument('--proposal', type=Path)
    override_parser.add_argument('--replace', action='store_true', help='Explicitly restore ledger state over unrecorded file edits')
    extraction = commands.add_parser('extract-capabilities', help='Prepare or run fixed-vocabulary LLM extraction')
    mode = extraction.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare', action='store_true')
    mode.add_argument('--run', action='store_true')
    extraction.add_argument('--api-format', choices=['openai-chat'])
    extraction.add_argument('--limit', type=int)
    commands.add_parser('competency-questions', help='Record execution coverage for the atomic competency catalogue')
    commands.add_parser('vocabulary', help='Export proposals clustering legacy tasks into the fixed SKOS v1 vocabulary')
    commands.add_parser('mappings', help='Refresh capability proposals from the entire database')
    commands.add_parser('database', help='Show counts for the single database and selected sample')
    import_parser = commands.add_parser('import', help='Synchronize both input sources into data/acg.sqlite3')
    import_parser.add_argument('--refresh-selection', action='store_true')
    commands.add_parser('normalize', help='Rebuild registry metadata from the existing cache, offline')
    collect_parser = commands.add_parser('collect', help='Refresh source snapshots over the network')
    collect_parser.add_argument('--source', choices=['curated', 'registry', 'skill-documents'], required=True)
    collect_parser.add_argument('--registry-pages', type=int, default=5)
    collect_parser.add_argument('--limit', type=int, help='Maximum pinned Skill documents to collect')
    args = parser.parse_args()
    if args.action == 'overrides':
        from . import override_history as history
        if args.operation == 'propose':
            if not args.section or not args.key: parser.error('propose requires --section and --key')
            history.propose(args.section,args.key)
        elif args.operation in ('record','refresh'):
            if not args.proposal: parser.error('record/refresh requires --proposal')
            if args.operation == 'record': history.record(args.proposal)
            else: history.refresh_proposal(args.proposal)
        elif args.operation == 'rebuild': history.rebuild(args.replace)
        else: getattr(history,args.operation)()
        return
    if args.action == 'extract-capabilities':
        from .llm_extraction import prepare, extract
        if args.prepare:
            prepare(args.limit)
        else:
            if not args.api_format: parser.error('--api-format is required for a live run')
            extract(args.api_format)
        return
    if args.action == 'competency-questions':
        from .query import competency_report
        competency_report()
        return
    if args.action == 'vocabulary':
        from .vocabulary import cluster_capabilities
        cluster_capabilities()
        return
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
        if args.action == 'collect' and args.source == 'skill-documents':
            from .skill_documents import collect_documents
            collect_documents(args.limit)
        elif args.action == 'collect' and args.source == 'curated':
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
