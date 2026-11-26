# SPARQL queries

See the maintained [competency questions](competency_questions.md) for
question definitions, expected examples and counterexamples.

All queries use `data/processed/agent_capability_graph.ttl` by default.
The graph is built exclusively from the unified `data/acg.sqlite3` database;
its current sample contains 10 servers, 55 tools and 110 Skills.
The additional Skill count can be changed through the frozen selection configuration.
The Python implementation is in `src/acg/query.py`; use `pipeline.py query` from the project root.
`queries/query_rdf.py` remains an optional shortcut to the same implementation.

```bash
.venv/bin/python pipeline.py run
.venv/bin/python pipeline.py query tools_for_web_search.rq
.venv/bin/python pipeline.py query skills_by_format.rq --format PDF
.venv/bin/python pipeline.py query skills_by_format.rq --format spreadsheet
.venv/bin/python pipeline.py query entity_capabilities.rq --name pdf
.venv/bin/python pipeline.py query entity_capabilities.rq --name 'Filesystem MCP Server'
.venv/bin/python pipeline.py query skill_requirements.rq --name phoenix-observability
```

`--graph path.ttl` selects an explicit file. The executable can be replaced by
`python` in an environment containing the root `requirements.txt` dependencies.

## Meaning of the answers

- `tools_for_web_search.rq` selects the normalized task `search / web`. Reading
  a URL or searching AWS documentation does not satisfy that task. The Brave
  assertion is supported by a pinned static registration and remains a review candidate.
- `skills_by_format.rq` finds description candidates, not normalized capability
  classifications. Results are grouped by canonical Skill, aggregating evidence URLs
  and showing one matching description (lexical minimum). Exclusions still need review.
- `entity_capabilities.rq` lists actual task assertions for the chosen name, including
  their method, review status and evidence type. Server assertions are explicitly
  derived from tool assertions. Several tasks or different resources sharing a name
  can produce several rows.
- `skill_requirements.rq --name phoenix-observability` selects a Skill by name;
  pass another name to inspect a different Skill. Missing dependency facts mean no requirement
  was recorded, not that no requirement exists. Compatibility, allowed tools and
  bundled files remain separate signals. Some requirements originate in secondary imports.

The automatic vocabulary is maintained in `config/capability_vocabulary.json`;
manual rules and review decisions are in `config/capability_overrides.json`.
`config/capability_mappings.json` is generated from those inputs and SQLite.
This is a project classification, not a primitive supplied by MCP or Skill formats.
Automatic mappings must match quoted description evidence and remain candidates.
An entity may expose several capabilities; query rows need not equal entity counts.
After editing vocabulary or overrides, run `pipeline.py build` to update query input.
Running `pipeline.py mappings` alone does not refresh the RDF.
See `reports/capabilities/review.csv` and `unclassified.csv` for the review queue.

SHACL structure and coverage reports are separate under `reports/validation/unified/`.
The placeholder `template-skill` is deliberately unclassified.


## Full-document evidence

```bash
.venv/bin/python pipeline.py query skill_body_evidence.rq
```

This query returns format mentions, requirement statements and installation
instructions from stored Skill bodies, with quotes, line numbers, sources and
review status. These candidates do not replace declared dependencies returned
by `skill_requirements.rq`. Some cached Skills lack complete documents; absence
of a body candidate therefore does not establish absence of a requirement.


For focused body-based discovery:

```bash
.venv/bin/python pipeline.py query skills_body_by_format.rq --format PDF
.venv/bin/python pipeline.py query skill_body_requirements.rq --name xlsx
```

The first query matches an exact normalized format mention (case insensitive),
not verified support. The second preserves dependency statements and installation
conditions; it does not flatten them into mandatory package requirements.


Identical evidence statements from GitHub and raw URLs are grouped into one
result row with aggregated source URLs. Different lines and different canonical
Skills remain separate, even when their preferred names coincide.


## Grouping tools by action

```bash
.venv/bin/python pipeline.py query tool_action_groups.rq
.venv/bin/python pipeline.py query tools_by_action.rq --action search
.venv/bin/python pipeline.py query tools_by_action.rq --action convert
.venv/bin/python pipeline.py query tools_by_action.rq --action list
```

Group counts are distinct canonical tool/server counts. Objects remain explicit,
so sharing a verb does not imply identical capabilities. These queries inspect
existing mappings; they do not perform unrestricted linguistic analysis or runtime
verification. The public HTTPS URI migration is documented in
[URI design](../docs/uri_design.md); current prefixes remain URNs.


## Numbered competency catalogue

All original identifiers CQ01–CQ20 now have numbered `.rq` files. Two compound
questions were split into CQ07b and CQ12b, giving **22 atomic questions** grouped
by tools, Skills, MCP servers and transversal concerns in
[competency_questions.md](competency_questions.md).

```bash
.venv/bin/python pipeline.py competency-questions
.venv/bin/python pipeline.py query cq03_skill_dependencies.rq --name phoenix-observability
.venv/bin/python pipeline.py query cq07b_tool_required_parameters.rq
.venv/bin/python pipeline.py query cq12b_skill_allowed_tools.rq
.venv/bin/python pipeline.py query cq16_skill_bundles.rq --bundle scripts
```

The coverage report records 25 executions (two CQ02 formats and three CQ16
bundle kinds). Descriptive query filenames above remain exploration helpers;
numbered files are the catalogue entry points. The catalogue documents all input
parameters and answer limitations. Empty results describe missing matching facts.
