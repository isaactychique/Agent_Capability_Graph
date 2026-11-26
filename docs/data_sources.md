# Collected data sources and project entry points

Snapshot: 2026-11-26. Links identify the providers; the imports and canonical
SQLite records retain the actual collection URLs, revisions and evidence.

## Initial collected corpus

The maintained manifest `data/sources/expanded_sources.json` defines the initial
10 MCP servers and 10 Skills, using these repositories:

- [Model Context Protocol reference servers](https://github.com/modelcontextprotocol/servers)
- [Brave Search MCP server](https://github.com/brave/brave-search-mcp-server)
- [GitHub MCP server](https://github.com/github/github-mcp-server)
- [Cloudflare MCP](https://github.com/cloudflare/mcp)
- [AWS MCP](https://github.com/awslabs/mcp)
- [Anthropic Skills](https://github.com/anthropics/skills)
- [Microsoft Skills](https://github.com/microsoft/skills)
- [Google Skills](https://github.com/google/skills)
- [Vercel Agent Skills](https://github.com/vercel-labs/agent-skills)

README evidence and pinned Skill packages are collected; these are software
metadata snapshots, not a runtime enumeration of deployed servers.

## Registry and additional Skill imports

- [Official MCP Registry](https://registry.modelcontextprotocol.io): server records.
- Model Context Protocol and Brave repositories above: exposed-tool registration evidence.
- Anthropic, Microsoft and Vercel repositories above: direct Skill metadata and bodies.
- [GitSkills](https://huggingface.co/datasets/mvaccargiu/gitskills): secondary sample;
  accepted graph inputs are distinct from the independently analyzed full dataset.

The normalized colleague corpus includes 502 distinct server records, 17 tools
and 272 Skills before merging with the initial source. Full source-level counts
and quarantine information are in `reports/imports/registry/source_counts.csv`.
The canonical SQLite store merges to 510 servers, 55 tools and 275 Skills.
Of those, 243 Skills have complete imported documents; 32 secondary-import
Skills lack a usable pinned direct body. Full GitSkills statistics do not mean
millions of Skills were imported into the RDF graph.

Lin's full GitSkills analysis pins dataset revision
`ebab17454a7c236f8f26b183567f1a126f42e3f8`; see `reports/gitskills/run_manifest.json`
and [the analysis README](../reports/gitskills/README.md). Large raw and derived
tables are outside Git. Additional metadata semantics and ontology extensions
remain a joint review item informed by Lin's field analysis.

## Project links

- [Ontology](../ontology/acg.ttl)
- [Fixed capability vocabulary v1 — draft SKOS](../ontology/capabilities_v1.ttl)
- [22 atomic competency questions and their SPARQL formulations](../queries/competency_questions.md)
- [Current selected graph](../data/processed/agent_capability_graph.ttl)
- [LLM prompt, automation and evaluation plan](llm_extraction.md)
- [Current reports](../reports/README.md)

## Ready-to-copy Mattermost update

The current collected sources, links and corpus boundaries are documented in
`docs/data_sources.md`. The ontology is in `ontology/acg.ttl`, the proposed fixed
20-concept SKOS vocabulary in `ontology/capabilities_v1.ttl`, and the proposed
22 atomic competency questions in `queries/competency_questions.md`, with linked SPARQL
queries. The selected graph contains 10 servers, 55 tools and 110 Skills.
LLM extraction inputs and a versioned prompt are prepared; EURECOM endpoint
configuration and joint review are pending. The 149-capability meeting snapshot
has since evolved to 154 detailed concepts, which remain available for comparison.

This is a message draft, not a message that has been sent. Links to new files on
GitHub require those changes to be published first.
