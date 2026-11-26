# Competency questions

This is the canonical catalogue for joint review with Lin. Questions are grouped
by their target resource and linked to executable SPARQL formulations in this folder.
The 20 original topic identifiers are retained for traceability. Splitting two
compound questions adds **CQ07b and CQ12b: 22 atomic questions in total**.
This follows the meeting target of approximately 20, rather than preserving
compound questions merely to keep an exact count.

Each question asks for one relation or one aggregate. Returned names, identifiers,
sources and review metadata provide context; they do not add a second question.
Format F, action A, resource R, Skill S and bundle kind B are parameters, not
conjunctions of separate requests. PDF and spreadsheets are separate executions.

Queries use `data/processed/agent_capability_graph.ttl`, the selected graph built
from the canonical SQLite database, rather than every entity in the database.
All questions have a SPARQL formulation using existing ontology predicates.
Execution success establishes expressibility, not semantic correctness or complete
source coverage. Zero rows mean no matching facts were recorded in this graph.

## MCP tools

| ID | Atomic competency question | SPARQL | Parameters / example | Interpretation and limitations |
| --- | --- | --- | --- | --- |
| CQ01 | Which tools can search the Web according to their recorded capabilities? | [cq01_web_search.rq](cq01_web_search.rq) | — | Mapped search/Web candidates; not runtime verification. |
| CQ05 | Which tools have the task action A? | [cq05_tools_by_action.rq](cq05_tools_by_action.rq) | `--action search` | Objects retain scope: searching documentation is distinct from searching the Web. |
| CQ07 | What input schemas are recorded for tools? | [cq07_tool_inputs.rq](cq07_tool_inputs.rq) | — | Raw schemas and schema descriptions are distinguished. |
| CQ07b | Which parameter names are explicitly recorded as required for tools? | [cq07b_tool_required_parameters.rq](cq07b_tool_required_parameters.rq) | — | Only explicit requiredParameter facts; no inference from schema strings. |
| CQ08 | What output schemas are recorded for tools? | [cq08_tool_outputs.rq](cq08_tool_outputs.rq) | — | Returns recorded schemas only. |

## Agent Skills

| ID | Atomic competency question | SPARQL | Parameters / example | Interpretation and limitations |
| --- | --- | --- | --- | --- |
| CQ02 | Which Skills are candidates for working with format F? | [cq02_skill_formats.rq](cq02_skill_formats.rq) | `--format PDF` | Lexical description matching; a format mention does not prove support. |
| CQ03 | Which dependencies are declared for Skill S? | [cq03_skill_dependencies.rq](cq03_skill_dependencies.rq) | `--name phoenix-observability` | Declared dependency facts only; compatibility and setup examples are separate. |
| CQ12b | Which tools are declared as allowed for Skills? | [cq12b_skill_allowed_tools.rq](cq12b_skill_allowed_tools.rq) | — | Recorded allowed-tools metadata; not enforcement verification. |
| CQ16 | Which Skills bundle files of kind B? | [cq16_skill_bundles.rq](cq16_skill_bundles.rq) | `--bundle scripts` | B is scripts, references or assets; run each value separately. Availability flags or recorded paths are evidence. |
| CQ18 | What compatibility constraints are recorded for Skills? | [cq18_compatibility.rq](cq18_compatibility.rq) | — | Source statements, not a compatibility test. |

## MCP servers

| ID | Atomic competency question | SPARQL | Parameters / example | Interpretation and limitations |
| --- | --- | --- | --- | --- |
| CQ09 | Which resources are exposed by MCP servers? | [cq09_server_resources.rq](cq09_server_resources.rq) | — | Requires collected resource inventories. |
| CQ10 | Which prompt templates are exposed by MCP servers? | [cq10_server_prompts.rq](cq10_server_prompts.rq) | — | Requires collected prompt inventories. |
| CQ14 | Which transports are documented for MCP servers? | [cq14_server_transports.rq](cq14_server_transports.rq) | — | Recorded configuration, not runtime connectivity. |

## Transversal questions

| ID | Atomic competency question | SPARQL | Parameters / example | Interpretation and limitations |
| --- | --- | --- | --- | --- |
| CQ04 | Which capabilities are associated with resource R? | [cq04_resource_capabilities.rq](cq04_resource_capabilities.rq) | `--name pdf` | Assertions include method and review status as context; server assertions are derived from tools. |
| CQ06 | What source evidence supports capability assertions for resource R? | [cq06_assertion_evidence.rq](cq06_assertion_evidence.rq) | `--name pdf` | Assertion/source identifiers, URLs and quotes when present; review counts belong to CQ20. |
| CQ11 | Which licenses are documented for graph resources? | [cq11_licenses.rq](cq11_licenses.rq) | — | Source context must be reviewed to distinguish file and repository licenses. |
| CQ12 | Which authentication requirements are recorded for graph resources? | [cq12_permissions.rq](cq12_permissions.rq) | — | Authentication only; allowed tools are CQ12b. |
| CQ13 | Which security risk signals are documented? | [cq13_security_signals.rq](cq13_security_signals.rq) | — | No automatic risk score is inferred. |
| CQ15 | Which software versions are documented? | [cq15_versions.rq](cq15_versions.rq) | — | Several snapshots may yield different versions. |
| CQ17 | Which repositories provide graph resources? | [cq17_repositories.rq](cq17_repositories.rq) | — | Repository identity alone does not establish entity equivalence. |
| CQ19 | Which graph resources lack a task annotation? | [cq19_unclassified.rq](cq19_unclassified.rq) | — | Missing classification does not mean no capability. |
| CQ20 | How many capability assertions have each review status? | [cq20_review_status.rq](cq20_review_status.rq) | — | Review status is distinct from model confidence. |

## Run the questions

From the repository root:

```bash
.venv/bin/python pipeline.py competency-questions
.venv/bin/python pipeline.py query cq01_web_search.rq
.venv/bin/python pipeline.py query cq02_skill_formats.rq --format PDF
.venv/bin/python pipeline.py query cq02_skill_formats.rq --format spreadsheet
.venv/bin/python pipeline.py query cq03_skill_dependencies.rq --name phoenix-observability
.venv/bin/python pipeline.py query cq04_resource_capabilities.rq --name pdf
.venv/bin/python pipeline.py query cq05_tools_by_action.rq --action search
.venv/bin/python pipeline.py query cq06_assertion_evidence.rq --name pdf
.venv/bin/python pipeline.py query cq07b_tool_required_parameters.rq
.venv/bin/python pipeline.py query cq12b_skill_allowed_tools.rq
.venv/bin/python pipeline.py query cq16_skill_bundles.rq --bundle scripts
.venv/bin/python pipeline.py query cq16_skill_bundles.rq --bundle references
.venv/bin/python pipeline.py query cq16_skill_bundles.rq --bundle assets
```

All other numbered queries need only their filename. `--graph path.ttl` selects
another RDF file. The coverage command runs 25 examples for the 22 questions:
two formats for CQ02 and three bundle kinds for CQ16. Results and execution
errors are recorded in `reports/queries/competency_coverage.csv`. Row counts
are query bindings, not necessarily distinct entity counts. An executable query
with zero rows is still a formulation; its data collection remains incomplete.

## Examples and counterexamples for review

- **CQ01:** `brave_web_search` is an expected candidate. Fetching a URL or
  searching only AWS documentation is not general Web search. Legacy object
  labels `web page` and `web content` accepted by the query require review.
- **CQ02:** `pdf` and `xlsx` are expected candidates for their respective formats.
  A prohibition, example or intermediate file can mention a format without
  establishing support. Description matching uses a regular expression and a
  limited exclusion heuristic. It does not establish operation-by-format support.
- **CQ03:** `arize-phoenix>=12.0.0` is a recorded dependency for
  `phoenix-observability`. An optional installation example in a Skill body is
  not automatically a mandatory dependency.
- **CQ04–CQ06:** a name can match multiple canonical entities. Entity/claim IRIs
  in the RDF identify them precisely. Source URLs alone do not prove a semantic
  classification. Quotes are optional; derived server assertions retain their
  links to supporting tool assertions in the RDF.
- **CQ07–CQ08:** schema text is not a normalized parameter model. Missing output
  schemas produce zero rows, rather than rows with unbound schema values.
- **CQ09–CQ10, CQ13:** missing inventories or risk observations must not be
  interpreted as absence of resources, prompts or security risks.
- **CQ19–CQ20:** `template-skill` is intentionally unclassified. A structural
  SHACL pass does not mean annotations have been reviewed by a human.

## Additional exploration queries

The descriptive filenames remain available as helpers and for existing commands:
`tools_for_web_search.rq`, `skills_by_format.rq`, `entity_capabilities.rq` and
`tools_by_action.rq` correspond to the numbered discovery queries. The numbered
files above define the catalogue used by the coverage command.

`tool_action_groups.rq` summarizes action groups. `skill_requirements.rq` gives
a broader metadata overview; `skill_body_requirements.rq` exposes conditional
body statements. `skills_body_by_format.rq` returns exact normalized format
mentions, including context, rather than verified support. `skill_body_evidence.rq`
provides quotes and line numbers for body facts. These helpers are not additional
numbered competency questions.

## Changes from the previous catalogue

- CQ01–CQ06 now have explicit numbered files alongside CQ07–CQ20.
- CQ03 focuses on declared dependencies; compatibility is CQ18 and allowed tools
  are CQ12b. Body evidence remains available through helper queries.
- CQ06 focuses on assertion evidence; review-status counts are CQ20.
- CQ07 covers input schemas; CQ07b covers required parameter names.
- CQ12 covers authentication; CQ12b covers Skills' allowed-tool declarations.
- CQ11 asks about licenses; a source column is provenance context.
- CQ16 takes one bundle kind per execution, avoiding a scripts/references/assets
  compound question.

The original CQ01–CQ10 review batch belongs to Isaac; CQ11–CQ20 remain draft
formulations for joint review with Lin. Added subquestions follow the parent
batch. Neither batch is presented as an approved review or submitted PR.
Collaborators still need to review wording, expected answers, counterexamples
and source semantics. Add those details whenever introducing a new question.

See [ontology](../ontology/acg.ttl), [capabilities](../docs/capabilities.md)
and [URI design](../docs/uri_design.md).
