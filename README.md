# Agent_Capability_Graph
Semester Project at EURECOM

## Tiny Search Prototype

The first prototype searches the example records using case-insensitive keywords. It uses only Python's standard library; no package installation is required.

From the project root, try:

```bash
python3 search.py search files
python3 search.py spreadsheet
python3 search.py read --type mcp_server
```

The search can find matching server tools as well as Skill descriptions. This is a simple baseline for testing the examples, not yet an RDF knowledge graph or semantic search engine.

## Mini Knowledge Graph

`data/mini_graph.jsonld` is a first JSON-LD graph made from the exploratory examples. It connects the Filesystem server to its four sampled tools, and the xlsx Skill to curator-assigned spreadsheet capabilities. It intentionally does not connect the Skill to the Filesystem server.

The `acg` vocabulary and `urn:acg:` identifiers are temporary project placeholders, not published identifiers. Capability labels are initial curator classifications, kept separate from the source descriptions. No package is required to check JSON syntax:

```bash
python3 -m json.tool data/mini_graph.jsonld > /dev/null
```

This checks JSON syntax only. Full JSON-LD expansion/querying can be added after the vocabulary and dependency choices are agreed.
