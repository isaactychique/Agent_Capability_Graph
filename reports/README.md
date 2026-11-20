# Project reports

## Current recorded snapshot

Documentation updated on 2026-11-20 from `database/summary.json`,
`corpus/summary.json`, `capabilities/coverage.json` and the generated RDF.
Counts describe the current stored artifacts and may change on the next import.

| Resource | Complete database | Selected RDF | RDF resources with assertions |
| --- | ---: | ---: | ---: |
| MCP servers | 510 | 10 | 10 |
| MCP tools | 55 | 55 | 55 |
| Agent Skills | 275 | 110 | 109 |

The database records 854 source records and 20,229 field observations.
The RDF has 6,808 triples, 151 capability concepts and 214 assertions.
Multiple assertions can describe a single resource. Server assertions derive
from tool assertions. No resource currently has a human-reviewed assertion.
The remaining unclassified Skill is `template-skill`, a placeholder description.

The most recent build compiled 10 automatic entity/source proposals from the
controlled vocabulary, alongside existing manual and static-registration rules.
Proposal counts are not counts of newly classified resources or unique tasks.
Extraction is limited to stored descriptions and supported vocabulary patterns;
full SKILL.md body extraction and runtime tool verification are not implemented.

## Report locations and producers

| Directory | Contents | Refresh command |
| --- | --- | --- |
| `database/` | Complete counts, canonical entities and identity reconciliation | `pipeline.py import` or `pipeline.py database` |
| `corpus/` | Selected graph counts, selection and merge decisions | `pipeline.py build` |
| `capabilities/` | Review queue and unclassified resources | `pipeline.py build` |
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

**Validation freshness:** SHACL was rerun on 2026-11-20 for the current
214-assertion graph. Structural validation passed; coverage reports one
unclassified resource (`template-skill`). Reports are in `validation/unified/`.
This result does not establish human review or runtime functionality.
