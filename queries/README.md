# SPARQL queries

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
.venv/bin/python pipeline.py query skill_requirements.rq
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
- `skill_requirements.rq` defaults to `phoenix-observability` in its `VALUES` clause;
  edit the name to inspect another Skill. Missing dependency facts mean no requirement
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
