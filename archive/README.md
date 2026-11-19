# Project history — not part of the active workflow

This folder preserves earlier material so that old configurations and prototypes do
not appear beside the active files. None of these files is read by `pipeline.py`.

| Folder | Contents |
| --- | --- |
| `config/` | Old configuration for two separate RDF exports |
| `graphs/` | Separate curated/registry graphs produced before integration |
| `prototypes/` | Initial keyword search, pilot collector and example JSON/JSON-LD |
| `launchers/` | Redundant entry scripts replaced by `pipeline.py` subcommands |
| `docs/` | Phase 0 notes, ontology draft and early README |
| `reports/` | Superseded validation reports |

These scripts are historical snapshots, not maintained runnable entry points.
Use the root README and `python pipeline.py --help` for the current workflow.

`cleanup_manifest.json` records the previous and current locations and SHA-256
hashes for individually moved files. Historical content was moved, not discarded.
Only generated Python bytecode and an empty obsolete package marker were removed.

CSV consultation tables were moved to the active `reports/curated/` and
`reports/registry/tables/` folders, separately from this archive. Their JSONL/SQLite
counterparts and all raw evidence remain in their original input locations.
