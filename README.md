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

## Metadata Collection Pilot

`collect_metadata.py` downloads revision-pinned snapshots from the MCP Servers and
Anthropic Skills GitHub repositories, keeps only the source files needed for the
current pilot in a temporary directory, and extracts metadata for two servers,
six tools, and three Skills. It stores field-level values, evidence status, source
URL, and repository revision in `data/interim/metadata.sqlite3`, and writes a
reviewable CSV to `data/interim/metadata_comparison.csv`.

Run it from the project root with:

```bash
python3 collect_metadata.py
```

The collector does not execute downloaded code. Some values are curator examples
or capability labels, not facts discovered automatically; each such field is
marked in `Evidence Status`. This is a reproducible pilot over known sources, not
yet a general web crawler or a complete download of runnable server/Skill
packages. The SQLite observations are kept separate from `data/sources/mini_graph.jsonld`
so they can be reviewed and mapped to the ontology before the graph is enriched.

## Expanded, Multi-source Dataset

`collect_expanded_metadata.py` builds the larger research sample from
`data/sources/expanded_sources.json`: at least 10 MCP servers with selected, documented
tools, and 10 Agent Skills from Anthropic, Vercel, Microsoft, and Google. For
each source it resolves and records a Git commit, saves the MCP README evidence,
and downloads each Skill directory as a ZIP under `data/raw/downloads/`. Downloaded
packages are not executed. Tool names and short descriptions are curated from
the pinned server documentation; this is a documented sample, not a claim that
the list exhausts each server's runtime tool API.

Run the expanded collector from the project root:

```bash
python3 collect_expanded_metadata.py
python3 generate_rdf.py
```

The expanded collector refreshes `data/interim/metadata.sqlite3` and
`data/interim/metadata_comparison.csv`; the RDF command then rebuilds
`data/processed/harvested_graph.ttl`. Use this expanded collector for the larger dataset:
the earlier `collect_metadata.py` is the small pilot and running it afterward
will replace the expanded SQLite/CSV snapshot with that pilot again. The
collector needs network access to the public GitHub API and raw repository
files; `generate_rdf.py` uses the `rdflib` dependency listed in
`requirements.txt`.

## Mini Knowledge Graph

`data/sources/mini_graph.jsonld` is a first JSON-LD graph made from the exploratory examples. It connects the Filesystem server to its four sampled tools, and the xlsx Skill to curator-assigned spreadsheet capabilities. It intentionally does not connect the Skill to the Filesystem server.

The `acg` vocabulary and `urn:acg:` identifiers are temporary project placeholders, not published identifiers. Capability labels are initial curator classifications, kept separate from the source descriptions. No package is required to check JSON syntax:

```bash
python3 -m json.tool data/sources/mini_graph.jsonld > /dev/null
```

This checks JSON syntax only. Full JSON-LD expansion/querying can be added after the vocabulary and dependency choices are agreed.

## Ontology (Turtle)

The first formal Turtle version is in `docs/acg_ontology.ttl`. It defines the
main classes and properties for MCP servers, tools, Skills, capabilities,
parameters, resources, prompts, software projects, directory listings, risk and
quality signals, and source-backed observations. It reuses Schema.org, SKOS,
PROV-O, RDF, RDFS, and OWL terms where appropriate.

The ontology namespace `urn:acg:ontology:` is provisional and intended for local
project work. Agree on a stable namespace before publishing graph data. The
existing JSON-LD remains an exploratory data graph and has not yet been migrated
to all of these ontology terms.

## SQLite to RDF Pipeline

`generate_rdf.py` converts the harvested SQLite records into the instance graph
`data/processed/harvested_graph.ttl`. It parses `docs/acg_ontology.ttl`, maps known entity
types and fields to ontology terms, preserves every field as a source-backed
`MetadataObservation`, connects tools to their servers, and represents curator
capability labels with explicit assertion and provenance nodes.

Install the Python dependency in the active virtual environment, then run:

```bash
python3 -m pip install -r requirements.txt
python3 generate_rdf.py
```

The Python package code lives in `src/acg/`; the root-level scripts are small
launchers kept so existing commands and IDE run configurations continue to
work. `data/sources/` contains maintained inputs, `data/raw/` contains
downloaded source snapshots, `data/interim/` contains collection outputs, and
`data/processed/` contains the generated RDF graph. Downloaded snapshots and
local Python environments are excluded from Git by `.gitignore`.

The command parses the ontology and generated Turtle and runs application-level
consistency checks (declared ACG terms, server/tool links, complete observations,
capability assertions, and declared domain/range expectations). This is not a
full OWL reasoner or SHACL validation. The expanded collector stores a collection
timestamp in SQLite, which the RDF generator uses for `acg:retrievedAt` on source
documents.
