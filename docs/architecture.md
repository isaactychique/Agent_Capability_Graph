# One database, one selected RDF graph

All imported MCP server, tool and Skill information is consolidated in
`data/acg.sqlite3`. `pipeline.py build` reads this single database. It does not
open separate SQLite/JSONL corpora and reconcile them again on every RDF build.
The original input snapshots are grouped under `data/imports/`.

## Data flow

```text
Initial corpus input                     Colleague's source corpus
 data/imports/curated/records.json         data/imports/registry/
                      \                  /
                       pipeline.py import
                              |
                     src/acg/database.py
                identity merging + observations
                              |
                       data/acg.sqlite3
              all entities + selected sample flag
                              |
      vocabulary + overrides -> pipeline.py mappings
                              |
                  capability_mappings.json
                              |
                       pipeline.py build
                RDF mapping + task annotations
                              |
          data/processed/agent_capability_graph.ttl
               inventory / SHACL / SPARQL queries
```

The working database currently contains 510 servers, 55 tools and 275 Skills.
The current selected RDF sample contains 10 servers, 55 tools and 110 Skills;
its additional Skill count is configurable.
The numbers follow identity reconciliation: two servers and seven Skills were
shared between the initial sample and the normalized colleague snapshot.

## Duplicate handling

A repeated source record is linked to one canonical entity; its values are kept
as observations rather than discarded or overwritten.

- Servers merge through explicit verified aliases, or matching repository and
  package identities. A matching repository and name is accepted only when package
  identities do not conflict. A repository alone is insufficient: a monorepo can
  contain many different MCP servers. Ambiguous matches cause an explicit error.
- Tools merge by **canonical server + exact tool name**. Distinct tool names from
  any duplicate server record are retained under that server. Different tool
  descriptions or schemas remain available in their source observations.
- Skills merge by **repository + SKILL.md path**. The same name in different
  packages or paths is not enough to merge. All matching source descriptions,
  requirements and package metadata are preserved.

The `in_sample` flag identifies the demonstration subset. Every known tool from
an imported record of a selected server belongs to that sample; no source's tools
replace another source's tool list.

## SQLite schema

| Table/view | Role |
| --- | --- |
| `entity` | One canonical identity, type, preferred name, optional parent and sample flag |
| `servers`, `tools`, `skills` | Readable views by entity type |
| `sample` | View of the demonstration subset |
| `source_record` | Original source IDs, complete input payloads and merge reasons |
| `observation` | Source-backed values, revisions and evidence statuses |
| `tool_annotation` | Imported static-registration assertions linked to canonical tools |
| `imported_observation` | Complete registry observations, including version/disposition information |
| `content_inventory` | Source content fingerprints and locations |
| `metadata` | Selection, manifest, collection metadata and schema version |

Foreign keys protect relationships. Import is performed into a temporary database,
checked for integrity, then atomically replaces the working database. A failed
import leaves the previous database intact. Reimport uses the same source inputs
and canonical identity rules rather than accumulating duplicate rows.

## Commands and updates

```bash
python pipeline.py import       # Synchronize the single database from both imports
python pipeline.py database     # Complete database and sample counts
python pipeline.py run          # Build the sample RDF, inventory it and run SHACL
python pipeline.py query tools_for_web_search.rq
```

The frozen selection and fingerprints remain in `config/corpus_selection.json`.
The selected source records and selection metadata are also stored in the database.
A normal RDF build uses that stored snapshot, so it works independently of the
import folders. After editing imports, run `import` to update the snapshot.

Collection and normalization need the optional dependencies:

```bash
python -m pip install -r src/acg/ingestion/requirements.txt
python pipeline.py normalize
python pipeline.py collect --source curated
python pipeline.py collect --source registry
```

These source-update commands synchronize the database after completing their input
updates. If a selected record changed, synchronization stops for review rather
than changing the sample silently. After reviewing a source/selection change:

```bash
python pipeline.py import --refresh-selection
python pipeline.py run
```

## File roles

`data/` is the single location for the working database, imports, raw evidence and
final graph. The local Python environment is in `.venv/` at the project root.
Import CSVs and statistics are in `reports/imports/`;
they describe the complete sources. `reports/database/` describes the unified
store; `reports/corpus/` describes the selected graph.

Task rules are compiled into `config/capability_mappings.json` from the database,
`config/capability_vocabulary.json` and `config/capability_overrides.json`. The
vocabulary normalizes supported phrases to shared action/object concepts.
Overrides preserve manual rules and entity review decisions. The generated
mappings may be removed and recreated; maintained inputs must be retained.
Annotations keep their source proofs. Automatic proposals remain review candidates;
explicit reviewed overrides require matching evidence before entering the RDF. SQLite consolidation does not imply
that every source server has a collected tool inventory or that every Skill has
been classified. SHACL structural and task-coverage checks remain separate.

The previous initial SQLite snapshot and obsolete graph copies, launchers and
prototypes have been removed after consolidation. The retained import snapshots
and source evidence are sufficient inputs for rebuilding the working database.

Historical `raw_file` values remain logical source locators. `paths.raw_path()`
resolves them into `data/imports/registry/raw/` after migration without rewriting
the selected source records or invalidating their fingerprints.


## Updating an expanding corpus

1. Collect or update source snapshots under `data/imports/`.
2. Run `pipeline.py import` to reconcile identities and replace the canonical store.
3. If selected source fingerprints changed, inspect the changes and use
   `pipeline.py import --refresh-selection` to accept a refreshed selection.
4. To enlarge the Skill subset, change `additional_skill_count` in
   `config/corpus_selection.json` before that refresh. The original Skills remain.
5. Run `pipeline.py run` to regenerate mappings, RDF, inventory and SHACL reports.

`import` also refreshes mappings. `mappings` alone updates configuration output,
not the RDF; `build` updates RDF and annotation/corpus reports, but not SHACL reports.
The database is rebuilt from snapshots rather than acting as an append-only log:
retain old source evidence separately when historical snapshots are required.

Implementation remains split by responsibility: `cli.py` dispatches commands,
`database.py` reconciles storage, `selection.py` freezes the sample, `build.py`
assembles RDF, `capabilities.py` extracts and applies task proposals, and query,
inventory and validation modules serve their corresponding commands. Collectors
and normalization code remain under `ingestion/`; they are not separate pipelines.
