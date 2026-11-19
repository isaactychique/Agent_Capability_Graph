# Phase 0 - Source Sample Notes

**Status:** exploratory source review, 2026-10-28. This is not the final data schema or RDF ontology. No server was run and no packages were installed.

## Sources reviewed

- **Filesystem MCP Server:** [official repository README](https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md), repository path src/filesystem/README.md, branch main (not pinned to a commit).
- **xlsx Agent Skill:** [Anthropic Skills repository](https://github.com/anthropics/skills/blob/main/skills/xlsx/SKILL.md), repository path skills/xlsx/SKILL.md, branch main (not pinned to a commit).

The two entries are useful for a file-and-spreadsheet sample. The reviewed sources do not state that the xlsx Skill depends on or uses the Filesystem MCP Server. Do not create that relationship without evidence.

## Metadata observed

| Field | Filesystem MCP Server | xlsx Skill |
|---|---|---|
| Identity | Name and official repository path | Skill name xlsx and official repository path |
| Description | Filesystem operations | Spreadsheet creation, reading, editing, analysis, and activation conditions |
| Capability details | 13 tools are documented; the current JSON sample contains four representative tools | Instructions are in SKILL.md; no separate capability taxonomy is declared |
| Inputs | Tool-specific input summaries are documented; full JSON input schemas are not recorded in this sample | Task/file conditions appear in the Skill description and instructions |
| Access and execution | stdio; allowed directories are passed as command-line arguments; Node.js 24 or later | Agent-platform compatibility is not documented in the reviewed Skill metadata |
| Effects / requirements | Tool annotations distinguish read-only and write-capable operations | Dependencies mentioned: openpyxl, pandas, markitdown, and LibreOffice for formula recalculation |
| License | MIT | Proprietary terms referenced through LICENSE.txt |
| Provenance | Source URL, path, branch, and retrieval date recorded | Source URL, path, branch, and retrieval date recorded |

## Competency-question coverage on this sample

| # | Question focus | Result from reviewed sources |
|---|---|---|
| 1 | Tools that query a SPARQL endpoint | No such tool is listed for this server. |
| 2 | Skills for spreadsheet work and when to use them | Answerable: the xlsx Skill describes supported file types, tasks, and activation conditions. |
| 3 | Servers that expose file-system operations | Answerable: the Filesystem MCP Server. |
| 4 | Which tools a Skill explicitly uses | Not documented for this pair; no Skill-to-server relationship is asserted. |
| 5 | Required tool inputs | Partially answerable from README summaries; full machine-readable schemas are not in the sample. |
| 6 | Read-only versus modifying operations | Answerable from the server's declared MCP tool annotations. Treat these as declared hints, not an independent security audit. |
| 7 | Transport, authentication, runtime, and access requirements | Partially answerable: stdio, Node.js, and allowed directories are documented; authentication is not documented. |
| 8 | Skill dependencies and supporting files | Partially answerable: dependencies and a recalculation script are referenced; platform compatibility is not documented. |
| 9 | MCP resources and prompts | Not documented in the reviewed server README; this does not prove they are absent. |
| 10 | Source and date for metadata | Partially answerable: source URLs and retrieval dates are recorded, but repository commits are not pinned and provenance is record-level. |
| 11 | Duplicate entries across directories | Cannot be answered from this two-entry sample. |
| 12 | Similar capabilities with different risks or dependencies | Not enough comparable entries yet. Some declared effects can be recorded for the Filesystem server. |

## Data-quality and modeling observations

- Keep not documented separate from not present and from not checked.
- Distinguish source-declared facts, such as MCP tool annotations, from later judgments or verification.
- input_summary is explanatory text, not a substitute for a tool's complete JSON Schema.
- The README overview mentions deleting directories, while its detailed tool list does not enumerate a delete tool. Verify the live tools/list result before recording deletion as an exposed operation.
- Source URLs and retrieval dates are useful provenance. Pinning a repository commit will be needed for a reproducible frozen dataset.
- The current sample is intentionally partial: four representative tools are recorded, not all 13 documented tools.

## Next phase 0 steps

1. Completed: review the three Dataset Search papers and record transferable lessons above.
2. Agree with the teammate on a small, representative source sample and division of work.
3. Use that sample to refine the metadata field list and competency questions before designing the RDF schema.

## Inspiration from the Dataset Search papers

**Scope note:** The empirical findings below concern dataset metadata. They are not measurements of MCP servers or Agent Skills. The transfer points are hypotheses and practices to consider for this project, not results that can be assumed to hold for our corpus.

### 1. Google Dataset Search: Building a Search Engine for Datasets in an Open Web Ecosystem

Noy, Burgess, and Brickley describe a search system that collects metadata published by many providers, then aggregates, normalizes, reconciles, deduplicates, and indexes it. They report challenges from inconsistent values, ambiguous use of vocabulary terms, repeated metadata on search-result pages, and equivalent records published by different repositories. They support Schema.org and DCAT rather than relying on only one vocabulary.

**Possible transfer to Agent Capability Graph:**

- Keep the source URL and the original metadata alongside any normalized value.
- Distinguish duplicate listings within one source from the same capability replicated across different sources.
- Compare candidate vocabularies, but do not assume one vocabulary covers every MCP or Skill-specific concept.
- Treat licensing and access requirements as useful discovery metadata, not incidental implementation details.

Source: [paper PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/4889.pdf), DOI 10.1145/3308558.3313685.

### 2. Google Dataset Search by the Numbers

Benjelloun, Chen, and Noy analyze a dated snapshot of the Dataset Search corpus. For their March 2020 snapshot, they report 28 million datasets from more than 3,700 sites. Their pipeline converts supported structured-data syntaxes to a common graph representation and performs cleaning and normalization at corpus, record, and property levels. Their analysis examines source domains, topics, formats, field population, and change over time. The authors also state that the corpus cannot measure all datasets on the Web because it depends on recognized metadata and crawl access.

**Possible transfer to Agent Capability Graph:**

- Make the sample date and retrieval date explicit; listings, repositories, and versions can change.
- Measure which metadata fields are populated in the selected sample before deciding which fields belong in a schema.
- Document the scope and blind spots of the selected sources. Not found in a chosen directory does not mean a capability does not exist.
- Report corpus composition (source, domain, capability area, and record type) so retrieval results can be interpreted in context.

Source: [arXiv paper PDF](https://arxiv.org/pdf/2006.06894), arXiv:2006.06894.

### 3. Dataset or Not? A Study on the Veracity of Semantic Markup for Dataset Pages

Alrashed et al. study whether pages marked as Schema.org/Dataset actually describe datasets. They report that pages from 61% of internet hosts providing that markup did not describe datasets. This is a result about hosts in their dataset-search setting, not a claim that 61% of individual records, MCP servers, or Skills are incorrect. Their work uses labeled examples to assess the reliability of the markup.

**Possible transfer to Agent Capability Graph:**

- A structured listing is evidence, but not proof, that its claims are correct.
- For a small sample, manually check important claims against their source, such as tool names, supported actions, dependencies, license, and access requirements.
- Define what counts as an MCP server, an MCP tool, an Agent Skill, and a capability before labeling or comparing records.
- Record whether a value is directly declared, normalized, inferred, independently checked, or still unknown.

Source: [Google Research paper PDF](https://storage.googleapis.com/gweb-research2023-media/pubtools/6282.pdf).

## Combined implications for our sample

1. Keep source provenance and retrieval dates. The current JSON does this at record level, but its GitHub branch references are not pinned to commits.
2. Preserve source wording separately from any normalized descriptions or capability labels.
3. Keep missing, not documented, and not checked as distinct states.
4. Treat MCP tool annotations as server-declared hints, not as independent security verification.
5. Check inconsistencies between a directory summary and a server's detailed tool list; the Filesystem sample provides one such case.
6. These three papers motivate quality and coverage checks; they do not justify reusing Dataset-specific classes or transferring dataset error rates to MCP and Skills.

No ontology or extraction pipeline has been selected from this reading alone.

## Source Inventory and Pilot Shortlist

**Reviewed:** 2026-10-28. The goal here is to shortlist sources for a small manual sample, not to start automated harvesting.

### MCP sources

| Source | Metadata available | Strength | Limitation / handling |
|---|---|---|---|
| Official MCP Registry | Versioned server name, title, description, repository and subfolder, package or remote transport, package identity/version, launch arguments, environment variables, and registry lifecycle metadata | Structured, paginated catalog with a machine-readable server.json format; useful for discovery and installation metadata | Entries are publisher-supplied and versioned. Unfiltered listings can include old versions; request version=latest or an exact version. The registry record does not replace tool-level metadata from the server source or runtime. License and tool schemas need checking in other sources. |
| modelcontextprotocol/servers repository | Per-server README, tool names/descriptions/input summaries, some MCP annotations, runtime and access requirements, and license | Maintained reference implementations with detailed source documentation; useful for tool-level fields | A limited reference-server collection, not a complete index of the ecosystem. Pin a repository revision when freezing collected examples. |
| github/github-mcp-server (optional comparison source) | Server setup, authentication, configurable toolsets, and GitHub API-related functionality | Adds a remote/service-oriented example that contrasts with the local Filesystem server | More setup and authorization detail to inspect; keep for a later sample if scope is tight. |

The Registry documentation describes one record per server version. When synchronizing, use the latest-version filter or request an exact version; do not assume the first text-sorted version is the newest. The registry's server.json is primarily server-level discovery and installation metadata. Tool schemas and actual available tools require a server-specific source or protocol inspection.

Sources: [Official MCP Registry API](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/api/official-registry-api.md), [server.json format](https://github.com/modelcontextprotocol/registry/blob/main/docs/reference/server-json/generic-server-json.md), [reference servers](https://github.com/modelcontextprotocol/servers), [GitHub MCP Server](https://github.com/github/github-mcp-server).

### Agent Skill sources

| Source | Metadata available | Strength | Limitation / handling |
|---|---|---|---|
| anthropics/skills | Skill folders and SKILL.md files with names, descriptions, instructions, and sometimes scripts or supporting files | Curated primary repository; good for examining complete Skill packages and comparing metadata with instructions | Represents one publisher/platform ecosystem. Licensing varies by Skill; inspect each Skill's license rather than assigning one repository-wide license. |
| skills.sh catalog and API | Stable skill ID, source repository, slug, install count, install URL, duplicate indicator, file tree/content and hash on detail lookup, and optional security-audit records | Broad discovery across repositories; offers useful source links, snapshot hashes, duplicate signals, and audit metadata | Third-party content is not guaranteed safe or high quality. Install counts indicate popularity, not capability quality. Audit records may be absent. The API documentation describes an OIDC-authenticated access path, so check API accessibility before planning automated harvesting. |

Sources: [Anthropic Skills repository](https://github.com/anthropics/skills), [skills.sh documentation](https://www.skills.sh/docs), [skills.sh API](https://www.skills.sh/docs/api).

### Pilot recommendation

- Use the Official MCP Registry to find and identify a server version, then consult that server's own repository for tool-level metadata. Keep the Filesystem server as the first local-server example.
- Use anthropics/skills for the first manually inspected Skill. Keep xlsx as the current example, but treat its license and metadata as specific to that Skill.
- Treat skills.sh as a candidate discovery source for a later, broader sample. Before using it for ingestion, verify the API access path and decide how to handle third-party content, absent audit records, popularity data, and detected duplicates.
- Keep the existing server and Skill as independent records unless a source explicitly documents a relationship.
- For each sample, capture the registry/listing record, source repository and path, exact version or commit when available, retrieval date, and whether each field came from a listing, README, SKILL.md, or live MCP response.

This is a proposed source shortlist for discussion with the teammate, not a final corpus decision.
