# SPARQL queries

All queries use `data/processed/agent_capability_graph.ttl` by default.
The Python implementation is in `src/acg/query.py`; use `pipeline.py query` from the project root.
`queries/query_rdf.py` remains an optional shortcut to the same implementation.

```bash
metadata/.venv/bin/python pipeline.py run
metadata/.venv/bin/python pipeline.py query tools_for_web_search.rq
metadata/.venv/bin/python pipeline.py query skills_by_format.rq --format PDF
metadata/.venv/bin/python pipeline.py query skills_by_format.rq --format spreadsheet
metadata/.venv/bin/python pipeline.py query entity_capabilities.rq --name pdf
metadata/.venv/bin/python pipeline.py query entity_capabilities.rq --name 'Filesystem MCP Server'
metadata/.venv/bin/python pipeline.py query skill_requirements.rq
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

The task vocabulary is configured in `config/capability_mappings.json`. It is a
project classification, not a primitive supplied by MCP or by the Skill format.
Mappings must match quoted description evidence and remain candidates pending review.
See `reports/capabilities/review.csv` and `unclassified.csv` for the review queue.

SHACL structure and coverage reports are separate under `reports/validation/unified/`.
The placeholder `template-skill` is deliberately unclassified.
