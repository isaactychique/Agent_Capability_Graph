# Agent Capability Graph

EURECOM project for representing, discovering and comparing MCP servers, MCP tools
and Agent Skills through source-backed RDF assertions and SPARQL queries.

The project maintains **one canonical SQLite database** and **one selected RDF
graph**. Current work follows the meeting decisions: a proposed list of 20
competency questions, a fixed 20-concept SKOS vocabulary, and reproducible LLM
extraction that selects from this vocabulary rather than freely inventing tasks.

## 1. Current state — November 26, 2026

| Measure | Complete SQLite corpus | Selected RDF graph |
| --- | ---: | ---: |
| Canonical MCP servers | 510 | 10 |
| Canonical MCP tools | 55 | 55 |
| Canonical Agent Skills | 275 | 110 |
| Skills with a complete imported SKILL.md | 243 | 105 |

The latest recorded RDF build contains **7,751 triples, 154 detailed capability
concepts and 221 capability assertions**. Assertions cover 10 servers, 55 tools
and 109 Skills. The remaining `template-skill` has a placeholder description.
The latest structural SHACL report passes; annotation coverage reports that one
unclassified Skill. No current assertion is marked as human-reviewed.

| Deliverable | Status |
| --- | --- |
| Canonical database, selected RDF, deterministic extraction, SPARQL and SHACL | Implemented and executed locally |
| 22 atomic competency questions and their formulations | Proposed for joint review; 25 query executions recorded without errors |
| Fixed SKOS vocabulary v1 | Draft of 20 concepts; requires joint review |
| Legacy-to-v1 grouping | 154 concepts analyzed: 113 single matches, 23 ambiguous, 18 unresolved; all proposals await review |
| Versioned LLM prompt and request preparation | Implemented; eight offline requests prepared for five selected Skills |
| EURECOM model execution | Not run; endpoint, model and API compatibility need confirmation |
| Keyword, tag and embedding baseline comparison | Evaluation protocol outlined; no benchmark scores measured |
| Public HTTPS identifiers | w3id.org selected; prefix request, hosting and migration pending |

The meeting snapshot of 149 capabilities and 6,765 triples is historical. The
current counts above reflect later enrichment, not a claim that the meeting
experiment was rerun. The historical ChatGPT prompt is unavailable in this repo;
the new prompt is separately versioned.

## 2. Start here

Run from the repository root with the existing environment:

```bash
source .venv/bin/activate
python pipeline.py database
python pipeline.py run
```

For initial environment setup:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

After modifying source snapshots, or when migrating a database without document
snapshots, synchronize before rebuilding:

```bash
.venv/bin/python pipeline.py import
.venv/bin/python pipeline.py run
```

`run` builds RDF, writes the annotation inventory, and executes SHACL. It does
not collect remote sources or call an LLM. Optional source collectors and the
independent full GitSkills analysis have additional documented dependencies.

## 3. How data reaches the graph

See the [complete architecture workflow](docs/workflow.md) for detailed Mermaid
diagrams, module responsibilities, SQLite relationships and command side effects.

```text
Curated snapshots + colleague's registry/Skill imports + pinned document caches
                                 |
                       import / identity reconciliation
                                 |
                        data/acg.sqlite3
                 all records, observations and documents
                                 |
                  frozen selected corpus + build
                                 |
        deterministic task mappings + source-located body candidates
                   + saved LLM selections, when available
                                 |
              data/processed/agent_capability_graph.ttl
                                 |
                 inventory / SHACL / SPARQL answers
```

Servers merge only through supported identity matches; their tool sets are
combined. Tools merge by canonical parent plus exact tool name. Skills merge
by repository and SKILL.md path. Different source values remain recorded as
observations. Sharing a repository or display name alone is insufficient.

The ordinary build reads entity/evidence data from SQLite, plus maintained
configuration and any validated saved LLM responses. Import snapshots and source
caches are reconstruction inputs, not competing working databases. Updating
SQLite does not silently expand a frozen Skill sample.

## 4. Two capability extraction paths

### Existing deterministic path

For the origin of the explicit rules and a complete `pdf` example, read
[capability provenance: from metadata to displayed answers](docs/capability_provenance.md).

Descriptions and full stored Skill bodies are matched against explicit rules.
Task assertions retain action/object pairs, matching evidence and source links.
Full-body evidence additionally records line, character offsets and SHA-256.
Servers derive their annotations from exposed tools; this is not runtime testing.

| File | Role |
| --- | --- |
| `config/capability_vocabulary.json` | Patterns for the existing fine-grained deterministic extractor |
| `data/curation/override_history.jsonl` | Captured legacy rules and future explicit decisions, with evidence snapshots |
| `config/capability_overrides.json` | Rule configuration reconstructed from that history; used by the extractor |
| `config/capability_mappings.json` | Generated artifact; can be deleted and rebuilt from maintained inputs and SQLite |
| `reports/capabilities/review.csv` | Generated task assertion review queue, not persistent decision input |
| `reports/capabilities/body_facts.csv` | Candidate format mentions, requirement statements and installation instructions |

A mention of PDF is not automatically proof of PDF support. An installation
command is not automatically a mandatory dependency. These body candidates stay
separate from declared dependency metadata. The small review worksheet in
`data/evaluation/skill_body_review.csv` preserves labels but is not a retrieval
benchmark or representative precision estimate.

### New fixed-vocabulary LLM path

**The following are different from the deterministic pattern file above:**

| File | Role |
| --- | --- |
| `ontology/capabilities_v1.ttl` | Proposed fixed list: 20 SKOS concepts, labels, definitions and scope notes |
| `config/capability_clusters_v1.json` | Lexical grouping rules proposing links from detailed legacy tasks to v1 concepts |
| `reports/vocabulary/legacy_clusters.csv` | Candidate, ambiguous and unresolved groupings; not accepted equivalences |
| `prompts/capability_extraction_v1.txt` | Versioned instructions, response format and examples |
| `reports/llm/requests.jsonl` | Prepared inputs including vocabulary, source, hash and text chunks |
| `src/acg/llm_extraction.py` | Preparation, explicit API adapter, response validation and saved-result application |

The LLM selects zero to five allowed concepts per text chunk and supplies exact
quotes with offsets. Unknown IDs and mismatching evidence are rejected. It can
abstain or suggest a missing concept, but suggestions never extend the vocabulary
automatically. Accepted technical validation still produces **human-review
candidates**, not approved classifications.

The 20-concept scheme has **not replaced the 154 detailed concepts**. Its grouping
is a draft, and no EURECOM results exist yet. When saved valid results are present,
the builder checks current vocabulary, prompt identity and SQLite evidence again
before emitting fixed-v1 assertions alongside legacy tasks. The full KG is not
claimed to contain only 20 capability nodes during this transition.

Prepare offline:

```bash
.venv/bin/python pipeline.py vocabulary
.venv/bin/python pipeline.py extract-capabilities --prepare --limit 5
```

Remove `--limit` to prepare all selected Skills. Preparation makes no network call.
Live execution requires the confirmed API protocol and environment variables
`ACG_LLM_ENDPOINT`, `ACG_LLM_MODEL` and optionally `ACG_LLM_API_KEY`. Only the
explicit `openai-chat` adapter is currently implemented; compatibility is not
assumed. Never commit credentials. See [LLM extraction](docs/llm_extraction.md).

### Rule origin and traceable revisions

The first explicit rules were exploratory assistant-assisted action/object choices
based on collected descriptions. Their original prompt and per-rule rationale
were not retained; checking an evidence phrase is not a retrospective justification
of those choices. Moving rules into the overrides file did not create provenance.

A new [curation register](docs/override_curation.md) captures 163 existing rules as
unreviewed legacy snapshots with evidence reconstructed now. It preserves unknown
original authorship rather than inventing it. Future revisions record actor,
rationale, rule, source, text fingerprint, quote and decision-chain references.

```bash
.venv/bin/python pipeline.py overrides audit
.venv/bin/python pipeline.py overrides propose --section skills --key pdf
.venv/bin/python pipeline.py overrides rebuild
```

The `pdf` proposal already exists, with actor/rationale left blank. Inspect it
before recording a decision. Keep `data/curation/override_history.jsonl` and its
`evidence/` files under version control. The override JSON can now be rebuilt
from that register; editing it directly causes an integrity mismatch. The
register tracks declared decisions and integrity, not authenticated signatures
or proof that every classification is semantically correct. See the linked guide
for evidence refresh, recording and recovery commands.

## 5. Competency questions and demonstrations

The [grouped competency-question catalogue](queries/competency_questions.md) links each question to
its queries, expected examples, counterexamples and limits. CQ01–CQ10 form
Isaac's first review batch. CQ11–CQ20 are executable discussion drafts for Lin's
batch, not a claim that Lin completed or approved them.

```bash
.venv/bin/python pipeline.py competency-questions
.venv/bin/python pipeline.py query tools_for_web_search.rq
.venv/bin/python pipeline.py query tools_by_action.rq --action search
.venv/bin/python pipeline.py query tool_action_groups.rq
.venv/bin/python pipeline.py query skills_by_format.rq --format PDF
.venv/bin/python pipeline.py query skills_by_format.rq --format spreadsheet
.venv/bin/python pipeline.py query skill_requirements.rq --name phoenix-observability
.venv/bin/python pipeline.py query skill_body_requirements.rq --name xlsx
.venv/bin/python pipeline.py query entity_capabilities.rq --name pdf
```

The execution report is `reports/queries/competency_coverage.csv`. There are 25
instantiations for 22 atomic questions: two formats for CQ02 and three bundle
kinds for CQ16. Zero rows
for resources, prompts or risk signals are currently collection gaps. Rows from
OPTIONAL queries do not prove their optional values are populated. Query
executability, ontology expressibility, data coverage and answer correctness
are distinct properties.

## 6. Collection, rebuilding and corpus growth

```bash
# Reconcile existing imports into SQLite; refresh generated mappings.
.venv/bin/python pipeline.py import
# Refresh mappings and document-candidate reports without rebuilding RDF.
.venv/bin/python pipeline.py mappings
# Rebuild RDF and annotation/corpus reports; SHACL is a separate step.
.venv/bin/python pipeline.py build
.venv/bin/python pipeline.py inventory
.venv/bin/python pipeline.py validate
```

To enlarge the Skill sample, edit `additional_skill_count` in
`config/corpus_selection.json`, inspect the intended source changes, then run:

```bash
.venv/bin/python pipeline.py import --refresh-selection
.venv/bin/python pipeline.py run
```

A changed selected record fingerprint also requires explicit selection refresh.
The full database remains larger than the selected graph. Registry servers
enter the RDF sample through collected tool evidence; a server metadata record
alone does not establish an exposed-tool inventory.

Pinned Skill bodies can be collected explicitly:

```bash
.venv/bin/python pipeline.py collect --source skill-documents
.venv/bin/python pipeline.py run
```

The recorded collection fetched 240 direct sources and verified their existing
SHA-256 values. Together with the original archives, they cover 243 canonical
Skills; 32 secondary imports lack usable pinned direct bodies. Snapshots are
in `data/imports/registry/skill_documents/`. Missing bodies remain explicit.

## 7. Validation and review boundaries

- `reports/validation/unified/report.*`: SHACL structural constraints.
- `reports/validation/unified/coverage.*`: resources lacking task annotations.
- `reports/capabilities/coverage.json`: per-type candidate/reviewed inventory.
- `reports/capabilities/documents.*`: full-document availability.

`validate --strict` fails on incomplete annotation coverage, including the known
template. Structural conformity does not establish semantic truth, source
trustworthiness, runtime functionality or human approval. Rebuild and rerun
validation after relevant source, configuration or shape changes.

## 8. Repository map and maintained inputs

```text
pipeline.py                     Main command; implementation in src/acg/cli.py
src/acg/                        Storage, extraction, graph, query and validation modules
src/acg/ingestion/               Source collection, normalization and GitSkills analysis
config/                         Selection, deterministic rules, overrides, grouping proposals
ontology/                       ACG ontology, SHACL constraints and fixed SKOS v1 scheme
prompts/                        Versioned LLM extraction instructions
queries/                        Executable SPARQL formulations
data/acg.sqlite3               Single canonical working store
data/imports/                  Source snapshots and document caches for reconstruction
data/raw/downloads/            Initial README evidence and pinned Skill packages
data/processed/                Selected RDF output
data/evaluation/               Retained manual evaluation worksheets
reports/                        Generated inventories, validation, vocabulary and query reports
reports/llm/                    Prepared inputs and future saved model-run artifacts
docs/                           Current project explanations and historical references
tests/                          Existing test suite
.venv/                          Single local Python environment
```

Keep source snapshots, the curation event history and referenced text, maintained
configuration, ontology, prompt and retained review decisions. RDF, generated mappings and most reports are rebuilt by their
producer commands; direct edits can be overwritten. `extract-capabilities --prepare` replaces the latest request set, and the small review worksheet is
maintained separately. Old report results should not be mistaken for a fresh run.

Lin's [full GitSkills analysis](reports/gitskills/README.md) is separate from the
selected graph. Its raw downloads and derived full tables remain outside Git;
its aggregate results do not mean millions of Skills entered the canonical KG.

## 9. Priorities and public identifiers

Next steps: joint vocabulary/question review; confirm the EURECOM endpoint and
run controlled extraction; inspect classification failures; publish the review
batches; then build the December keyword/tag/embedding comparison with fixed
queries and judged expected answers. No baseline scores are available yet.

w3id.org is selected, with `https://w3id.org/agent-capability-graph` proposed for
the namespace request. Registration, target hosting and coordinated migration
are pending. The graph and queries still use provisional URNs. This publication
work follows the agreed vocabulary and extraction deliverables.

## Documentation

- [Override curation: audit, revision and reconstruction](docs/override_curation.md)

- [Capability provenance: sources, overrides and displayed answers](docs/capability_provenance.md)

- [Complete architecture and execution workflow](docs/workflow.md)

- [November 26 deliverables and remaining work](docs/november_26_deliverables.md)
- [Collected sources, links and draft Mattermost update](docs/data_sources.md)
- [Competency questions](queries/competency_questions.md)
- [Fixed-vocabulary LLM extraction and evaluation protocol](docs/llm_extraction.md)
- [Database and pipeline architecture](docs/architecture.md)
- [Capabilities, evidence and review](docs/capabilities.md)
- [SHACL validation](docs/validation.md)
- [SPARQL usage](queries/README.md)
- [Report guide](reports/README.md)
- [Proposed public URI design](docs/uri_design.md)

The full-corpus analysis extends the original 180-row sample at a pinned dataset
revision. Code is in `src/acg/ingestion/gitskills/`, aggregate results are in
`reports/gitskills/`, and tests are in `tests/test_gitskills*.py`.
See [results, counting definitions and reproduction commands](reports/gitskills/README.md).
Raw downloads and full derived tables remain outside Git. This analysis does not
change the selected RDF corpus or existing source snapshots.

## November 26: Lin's metadata analysis and review proposal

- [Lin's original 20-question proposal and proposed split](docs/nov26/competency_questions.md)
- [Additional metadata values and ontology recommendations](docs/nov26/metadata_mapping.md)
- [Exact-content deduplication: guarantees and limits](docs/nov26/deduplication.md)
- [Capability extraction prompt and integration handoff](docs/nov26/capability_extraction.md)
- [CQ11–20 snapshot results](reports/nov26/query_audit.json)

The joint question list and production SKOS vocabulary still require coordination;
query execution does not imply retrieval accuracy or completed LLM integration.

The maintained [atomic competency catalogue](queries/competency_questions.md)
uses different CQ identifiers from Lin's original proposal under `docs/nov26/`.
Those identifiers are local to each catalogue and require joint reconciliation.
The pipeline prompt remains `prompts/capability_extraction_v1.txt`; Lin's
description-only contract is preserved separately as
`prompts/capability_extraction_description_v1.txt` with its renderer.
