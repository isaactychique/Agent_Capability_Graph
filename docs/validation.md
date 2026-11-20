# SHACL validation

```bash
.venv/bin/python pipeline.py validate
.venv/bin/python pipeline.py validate --strict
```

The code is in `src/acg/validation.py`, and the shapes are in `ontology/`.
The pySHACL engine also validates the shapes with Meta-SHACL. OWL reasoning is
not enabled. A graph without an MCP server is rejected.

`shapes.ttl` requires a single name per resource, sources, parent servers for tools,
normalized tasks, and assertion methods and statuses. A server's derived assertions
must point to an assertion for the same task on one of its exposed tools.

`coverage.ttl` separately identifies servers, tools, and Skills without an assertion.
This absence means a classification is missing, not that the resource lacks capabilities.
The graph retains an explicit example: `template-skill`, which has a placeholder description.

The files `reports/validation/unified/report.txt` and `report.ttl` cover structure;
`coverage.txt` and `coverage.ttl` cover annotation coverage.
Without `--strict`, only a structural validation failure causes exit code 1.
With `--strict`, an unclassified resource also causes exit code 1.
Neither check turns a candidate annotation into a reviewed annotation.

Tests are grouped under `tests/`. Install the main dependencies and those in
`src/acg/ingestion/requirements.txt` for the complete suite, then run:

```bash
python -m unittest discover -s tests -v
```


## Keeping reports current

`build` regenerates RDF and annotation reports but does not rerun SHACL.
`mappings` regenerates only the mapping artifact. After either vocabulary or
review changes, use `pipeline.py run` to rebuild the graph and refresh both
validation reports. Existing SHACL files describe the graph at their last
validation run; do not assume they validate a subsequently rebuilt graph.

A reviewed entity override is applied only if its evidence matches. SHACL checks
shape constraints and coverage; it does not establish that an extraction is
semantically correct or that a tool was executed successfully.
