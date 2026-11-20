# Agent Capability Graph

An EURECOM project: one canonical SQLite database for MCP servers, tools, and
Agent Skills, and one selected RDF graph for discovery and validation.

## Start here

From the repository root:

```bash
.venv/bin/python pipeline.py database
.venv/bin/python pipeline.py run
```

The **single working database is `data/acg.sqlite3`**. It contains both sources,
merged identities, all imported descriptions and observations, and tool-to-server
relationships. The ordinary RDF build reads this database only.

The current RDF sample contains **10 servers, 55 tools, and 110 Skills**, as selected for
the demonstration. The database also retains the rest of the source corpus:
currently 510 distinct servers, 55 tools, and 275 Skills. These larger counts are
not claims about runtime tool availability.

For a new checkout or after editing imported data, synchronize the database first:

```bash
.venv/bin/python pipeline.py import
.venv/bin/python pipeline.py run
```

Use `python -m pip install -r requirements.txt` to prepare a different environment;
then replace `.venv/bin/python` with `python`.

## Files for everyday work

| Task | File |
| --- | --- |
| Inspect the complete unified database | `data/acg.sqlite3` |
| Query the selected RDF graph | `data/processed/agent_capability_graph.ttl` |
| Inspect the selected 100 additional Skills | `config/corpus_selection.json` |
| Edit extraction vocabulary | `config/capability_vocabulary.json` |
| Preserve manual rules and review decisions | `config/capability_overrides.json` |
| Inspect generated task mappings | `config/capability_mappings.json` |
| Inspect database counts and identity reconciliation | `reports/database/` |
| Examine annotations and their evidence | `reports/capabilities/review.csv` |
| Inspect unclassified resources | `reports/capabilities/unclassified.csv` |
| Read SHACL results | `reports/validation/unified/` |

The RDF graph has candidate annotations for all 10 servers, all 55 tools and
109 Skills. The remaining `template-skill` has a placeholder description.
All task annotations still await human review.

## Commands

```bash
python pipeline.py import
python pipeline.py database
python pipeline.py mappings
python pipeline.py build
python pipeline.py inventory
python pipeline.py validate
python pipeline.py query tools_for_web_search.rq
python pipeline.py query skills_by_format.rq --format PDF
python pipeline.py query entity_capabilities.rq --name pdf
```

`run` combines building, inventory and validation. `validate --strict` also fails
on incomplete annotation coverage, so the placeholder Skill causes an expected failure.
`pipeline.py --help` lists all commands.

## Organization

```text
pipeline.py                 Main command
src/acg/database.py         Unified storage and identity reconciliation
src/acg/                   Graph building, task annotations, queries and validation
config/                    Sample selection, vocabulary, overrides and generated mappings
ontology/                  RDF vocabulary and SHACL constraints
queries/                   SPARQL query files
data/acg.sqlite3           Single working database
data/imports/curated/      Initial corpus input snapshot (JSON)
data/imports/registry/     Colleague's source cache and normalized import files
data/raw/downloads/        Initial downloaded README and Skill package evidence
data/processed/            Selected RDF graph
reports/database/          Complete database counts and identity mappings
reports/corpus/            Selected graph counts and selection decisions
reports/capabilities/      Task annotations, evidence and coverage
reports/validation/        SHACL results
reports/imports/           Import-level CSVs and collection statistics
tests/                     Tests
docs/                      Current documentation and reference reports
.venv/                     Local Python environment
```

The files in `data/imports/` are import snapshots and evidence, not competing
working databases. Obsolete graph copies, launchers, prototypes and the previous
SQLite input have been removed after consolidation. Direct edits to imported data require
`pipeline.py import`; direct edits to generated RDF or reports are overwritten.

Further reading:

- [Database and pipeline architecture](docs/architecture.md)
- [Capabilities, evidence, and review](docs/capabilities.md)
- [SHACL validation](docs/validation.md)
- [SPARQL queries](queries/README.md)
- [Reports and current results](reports/README.md)


## Capability generation and corpus growth

`import`, `build` and `run` regenerate `config/capability_mappings.json` from
SQLite descriptions, `config/capability_vocabulary.json` and persistent
`config/capability_overrides.json`. The generated file can be deleted and rebuilt;
the vocabulary and overrides are maintained inputs and must be retained.
Use `.venv/bin/python pipeline.py mappings` to regenerate mappings independently.
A resource can have several tasks, each supported by source-matched evidence.
Automatic matches remain candidates. The extractor currently reads descriptions,
not complete SKILL.md bodies, and its vocabulary is intentionally limited.

To expand the sample, edit `additional_skill_count` in
`config/corpus_selection.json`, then run:

```bash
.venv/bin/python pipeline.py import --refresh-selection
.venv/bin/python pipeline.py run
```

Imports synchronize the full corpus. The RDF subset stays frozen until explicitly
refreshed; source changes can require refreshing selected-record fingerprints.
Registry servers enter the sample through collected tool evidence; a database
record alone does not establish a server's tool inventory.
See [capabilities and persistent review](docs/capabilities.md) for extraction and
review details. Current generated results contain 6,808 triples, 151 capability
concepts and 214 assertions; these are snapshot counts, not fixed constraints.

## Full GitSkills metadata analysis

The full-corpus analysis extends the original 180-row sample at a pinned dataset
revision. Code is in `src/acg/ingestion/gitskills/`, aggregate results are in
`reports/gitskills/`, and tests are in `tests/test_gitskills*.py`.
See [results, counting definitions and reproduction commands](reports/gitskills/README.md).
Raw downloads and full derived tables remain outside Git. This analysis does not
change the selected RDF corpus or existing source snapshots.
