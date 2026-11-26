# Project reports

## Current recorded snapshot

Documentation updated on 2026-11-25 from `database/summary.json`,
`corpus/summary.json`, `capabilities/coverage.json` and the generated RDF.
Counts describe the current stored artifacts and may change on the next import.

| Resource | Complete database | Selected RDF | RDF resources with assertions |
| --- | ---: | ---: | ---: |
| MCP servers | 510 | 10 | 10 |
| MCP tools | 55 | 55 | 55 |
| Agent Skills | 275 | 110 | 109 |

The database records 854 source records and 20,229 field observations.
The RDF has 7,751 triples, 154 capability concepts and 221 assertions.
Multiple assertions can describe a single resource. Server assertions derive
from tool assertions. No resource currently has a human-reviewed assertion.
The remaining unclassified Skill is `template-skill`, a placeholder description.

The most recent build compiled 36 automatic entity/source/occurrence proposals from the
controlled vocabulary, alongside existing manual and static-registration rules.
Proposal counts are not counts of newly classified resources or unique tasks.
Extraction uses stored descriptions and 243 available full SKILL.md bodies, with
supported vocabulary patterns. Runtime tool verification is not implemented.
Of 275 canonical Skills, 32 have no imported complete body. There are 182 body
fact candidates: 48 format mentions, 68 requirement statements and 66 installation
instructions. These counts cover the entire database; RDF includes only the
selected sample. The manual evaluation worksheet remains pending; no accuracy score
is claimed. See `../data/evaluation/skill_body_review.csv`.

## Report locations and producers

| Directory | Contents | Refresh command |
| --- | --- | --- |
| `database/` | Complete counts, canonical entities and identity reconciliation | `pipeline.py import` or `pipeline.py database` |
| `corpus/` | Selected graph counts, selection and merge decisions | `pipeline.py build` |
| `capabilities/` | Review queue and unclassified resources | `pipeline.py build` |
| `capabilities/documents.*`, `body_facts.csv` | Full-document availability and source-located fact proposals | `pipeline.py mappings` or `pipeline.py build` |
| `capabilities/coverage.json` | Annotation inventory by resource type | `pipeline.py inventory` |
| `validation/unified/` | SHACL structure and annotation coverage | `pipeline.py validate` |
| `imports/` | Source-level comparison, normalization statistics, tables and figures | Source collection/normalization commands |

All commands run from the repository root with `.venv/bin/python` before
`pipeline.py`. The `unified` directory name denotes the one final graph; it is
not a second database or another graph.

## Configuration and review

- `../config/capability_vocabulary.json` defines reusable automatic concepts.
- `../config/capability_overrides.json` retains manual mappings and entity decisions.
- `../config/capability_mappings.json` is generated and can be recreated.
- `capabilities/review.csv` is output for inspection, not persistent review input.

Entity overrides can retain reviewed or rejected decisions. A reviewed mapping
must still match source evidence. Static-registration assertions are independent
of entity overrides; derived server assertions remain review candidates.
See [capability rules and review](../docs/capabilities.md) for the supported format.

## Refreshing the complete reporting set

After updating source snapshots:

```bash
.venv/bin/python pipeline.py import
.venv/bin/python pipeline.py run
```

If selected records changed, inspect them and explicitly refresh selection with
`import --refresh-selection`. Increase `additional_skill_count` in
`../config/corpus_selection.json` before this refresh to enlarge the Skill sample.
The database retains all imported entities even when outside the selected RDF.

`run` rebuilds RDF, inventories annotations and runs SHACL. Structural conformity,
annotation coverage and human review are separate measures. `validate --strict`
also fails when a resource is unclassified, including the placeholder Skill.

**Validation freshness:** SHACL was rerun on 2026-11-25 for the current
221-assertion graph. Structural validation passed; coverage reports one
unclassified resource (`template-skill`). Reports are in `validation/unified/`.
This result does not establish human review or runtime functionality.


## Pinned document collection

`pipeline.py collect --source skill-documents` fetched 240 pinned direct sources
on 2026-11-25. All downloaded SHA-256 values matched the existing metadata.
The 32 secondary imports were skipped. See
`capabilities/document_collection.json` for per-source statuses. The original
10 archives and 240 registry files overlap on seven canonical identities,
yielding 243 Skills with full documents. This changes document coverage, not
the selected RDF resource counts.


## Competency questions and action groups

The maintained question catalogue is in
[competency_questions.md](../queries/competency_questions.md). The proposed public
identity policy is in [uri_design.md](../docs/uri_design.md); HTTPS migration is
pending acceptance of the proposed w3id.org prefix and target hosting.

On 2026-11-25, `tool_action_groups.rq` returned 17 mapped action groups:
`search` includes 11 canonical tools, `list` includes 6, and `convert` includes
1 (`convert_time`, object `timezone`). Membership may overlap across groups.
These counts summarize existing candidate annotations, not runtime verification.


## November 26 follow-up artifacts

- `queries/competency_coverage.csv`: execution status/counts for 22 atomic questions,
  25 instantiations. Executability is not retrieval accuracy.
- `vocabulary/legacy_clusters.csv` and `summary.json`: 154 current detailed concepts
  proposed against 20 SKOS concepts; 113 single matches, 23 ambiguous, 18 unresolved.
- `llm/requests.jsonl`: eight offline prompt packets for five selected Skills.
  No EURECOM model was called. Live response artifacts will be saved separately.

See [meeting deliverables](../docs/november_26_deliverables.md) for pending joint
review, publication and endpoint configuration. Meeting counts (149 concepts,
6,765 triples) are historical; they are not overwritten by current counts.


## Explicit-rule curation

`curation/override_audit.json` reports event-chain integrity, output consistency
and captured evidence availability. The authoritative history and evidence are
in `../data/curation/`, not this generated report. The initial capture contains
163 unreviewed legacy rules; matching current source text does not recreate their
missing historical rationale. See [the revision workflow](../docs/override_curation.md).

## Lin's merged analysis and query proposal

`gitskills/values-2026-11-26/` contains additional-field distributions and evidence
examples from the full dataset. `nov26/` preserves a separate query audit whose
graph hash identifies an older snapshot; its counts are not the current root
catalogue's counts. Queries now reside in `queries/lin_queries/`, with paths in
`docs/nov26/lin_queries.json`. The standalone audit command regenerates that
report; normal `pipeline.py run` does not refresh it. Question numbering is local
to each proposal until joint reconciliation.
