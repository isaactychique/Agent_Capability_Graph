# Supervisor demo commands — November 26, 2026

Run from the project root. These commands use the existing `.venv` and local data.

## 1. Setup and command discovery

```bash
cd /home/dakiotychique17/EURECOM_PROJECT/Agent_Capability_Graph
source .venv/bin/activate
python pipeline.py --help
```

## 2. Database and complete offline workflow

```bash
python pipeline.py database
python pipeline.py run
```

`run` builds the selected RDF, prints its inventory and runs SHACL. It does not
collect new sources or call a remote LLM. Current recorded graph: 10 servers,
55 tools, 110 Skills, 7,751 triples and 221 assertions. Counts may change after
source updates. Structural validation passes; coverage retains `template-skill`.

Individual stages, if explaining the pipeline step by step:

```bash
python pipeline.py import
python pipeline.py mappings
python pipeline.py build
python pipeline.py inventory
python pipeline.py validate
```

`import` synchronizes local inputs; `mappings` generates mapping proposals but
does not rebuild RDF. `build` also generates mappings. These producer commands
update generated artifacts; they are alternatives to the short `run` sequence.

## 3. All numbered competency queries

```bash
python pipeline.py query cq01_web_search.rq
python pipeline.py query cq02_skill_formats.rq --format PDF
python pipeline.py query cq02_skill_formats.rq --format spreadsheet
python pipeline.py query cq03_skill_dependencies.rq --name phoenix-observability
python pipeline.py query cq04_resource_capabilities.rq --name pdf
python pipeline.py query cq05_tools_by_action.rq --action search
python pipeline.py query cq06_assertion_evidence.rq --name pdf
python pipeline.py query cq07_tool_inputs.rq
python pipeline.py query cq07b_tool_required_parameters.rq
python pipeline.py query cq08_tool_outputs.rq
python pipeline.py query cq09_server_resources.rq
python pipeline.py query cq10_server_prompts.rq
python pipeline.py query cq11_licenses.rq
python pipeline.py query cq12_permissions.rq
python pipeline.py query cq12b_skill_allowed_tools.rq
python pipeline.py query cq13_security_signals.rq
python pipeline.py query cq14_server_transports.rq
python pipeline.py query cq15_versions.rq
python pipeline.py query cq16_skill_bundles.rq --bundle scripts
python pipeline.py query cq16_skill_bundles.rq --bundle references
python pipeline.py query cq16_skill_bundles.rq --bundle assets
python pipeline.py query cq17_repositories.rq
python pipeline.py query cq18_compatibility.rq
python pipeline.py query cq19_unclassified.rq
python pipeline.py query cq20_review_status.rq
```

Catalogue: [competency_questions.md](../queries/competency_questions.md).
Execute all 25 examples for the 22 atomic questions and export counts:

```bash
python pipeline.py competency-questions
cat reports/queries/competency_coverage.csv
```

Empty results indicate no matching recorded facts. Executability is not semantic
correctness or complete source coverage. Format discovery returns candidates.

## 4. Action groups and full-document evidence

```bash
python pipeline.py query tool_action_groups.rq
python pipeline.py query tools_by_action.rq --action list
python pipeline.py query tools_by_action.rq --action convert
python pipeline.py query skill_body_evidence.rq
python pipeline.py query skills_body_by_format.rq --format PDF
python pipeline.py query skills_body_by_format.rq --format XLSX
python pipeline.py query skill_body_requirements.rq --name xlsx
python pipeline.py query skill_requirements.rq --name phoenix-observability
```

Body statements retain context; they are not automatically mandatory dependencies.
`convert_time` concerns timezones, not file conversion. Sharing an action does
not imply sharing the same object or task.

## 5. SHACL and annotation coverage

```bash
python pipeline.py validate
cat reports/validation/unified/report.txt
cat reports/validation/unified/coverage.txt
```

Optional negative demonstration:

```bash
python pipeline.py validate --strict
```

An exit code of 1 is expected while `template-skill` remains unclassified.
Structural conformance does not establish human approval or runtime availability.

## 6. Capability-rule provenance

```bash
python pipeline.py overrides audit
python pipeline.py overrides propose --section skills --key pdf
```

The second command creates or retains an editable proposal; it records no
approval. Show `config/capability_overrides.json`, generated
`config/capability_mappings.json`, `data/curation/override_history.jsonl`, and
`reports/curation/`. Historical rules are unreviewed legacy snapshots; the original
creation prompt is unavailable. See [curation guide](override_curation.md) for
recording real decisions and reconstructing the configuration.

## 7. SKOS vocabulary and offline LLM preparation

```bash
python pipeline.py vocabulary
cat reports/vocabulary/summary.json
python pipeline.py extract-capabilities --prepare --limit 5
```

Show `ontology/capabilities_v1.ttl`, `prompts/capability_extraction_v1.txt`, and
`reports/llm/requests.jsonl`. Preparation replaces the latest request set; it
makes no network call. The 20-concept SKOS vocabulary is a draft; detailed task
annotations are still distinct from these proposed groups.

Live extraction is a separate step, requiring confirmed endpoint/model details
and configuration of `ACG_LLM_ENDPOINT`, `ACG_LLM_MODEL` and optionally
`ACG_LLM_API_KEY` in the environment. Once configured:

```bash
python pipeline.py extract-capabilities --run --api-format openai-chat
python pipeline.py run
```

This live step has not been demonstrated against EURECOM. Do not present the
offline request packets as model responses or evaluated results.

## 8. Report PDF

```bash
latexmk -pdf -cd docs/fifth_progress_report.tex
```

## Files to show

- `data/acg.sqlite3`: canonical database.
- `data/processed/agent_capability_graph.ttl`: graph queried by default.
- `ontology/acg.ttl`: ontology.
- `ontology/shapes.ttl` and `ontology/coverage.ttl`: validation constraints.
- `queries/competency_questions.md`: grouped atomic questions.
- `docs/workflow.md`: full architecture and workflow.
- `docs/uri_design.md`: proposed HTTPS identifiers; w3id prefix not yet reserved.

For a short demo, run sections 1–2, CQ01–CQ06, the body requirements helper,
then sections 5–7. Use the complete catalogue when discussing ontology coverage.
