# Phase 0 Meeting Deliverables: Sample and Candidate Vocabulary

**Prepared:** 2026-11-04  
**Status:** Discussion draft for the Thursday progress meeting. This is not the final schema, ontology, or RDF dataset.

## 1. Current Progress

- **Pilot examples:** the Filesystem MCP server and Anthropic's xlsx Agent Skill. They are independent examples; the reviewed sources do not establish that the Skill uses this server.
- **Tool sample:** four representative Filesystem tools are recorded (`read_text_file`, `write_file`, `search_files`, `list_allowed_directories`). The repository README documents more; this JSON is a sample, not a complete server inventory.
- **Skill sample:** the xlsx description, instructions summary, license, dependencies, and referenced recalculation script are recorded.
- **Prototype:** a local Python keyword search over `data/examples.json` was tested with `search files` and `spreadsheet`. It retrieves the expected tool and Skill, respectively. It is a baseline, not semantic search or an RDF graph.
- **Background:** the three Dataset Search papers and 12 draft competency-question topics are documented in `docs/notes.md`.

Source snapshot in the examples: 2026-10-28, from repository `main` branches that are not commit-pinned. The source and branch may have changed since collection; pin exact revisions before treating the sample as reproducible.

## 2. Field Inventory and Coverage

| Information area | Filesystem MCP server / tools | xlsx Agent Skill | Initial modeling implication |
|---|---|---|---|
| Identity | Server name, repository/path, transport, runtime, license; four tool names recorded | Skill name, repository/path, license | Give each server, tool, and Skill its own identifier and entity type. Do not merge a tool into its server record. |
| Capability and selection | Server-level filesystem summary; individual tool names, descriptions, and selected input summaries | Long description states what tasks/file types trigger the Skill and what is out of scope; instructions add procedures | Preserve source descriptions. Store a normalized capability concept separately from the source wording. |
| Interface | Tool input summaries are present, but the sample does not store full MCP JSON Schemas | File/task conditions and procedural guidance; no MCP invocation interface is stated | Store full `inputSchema`/optional `outputSchema` for MCP tools when obtained. Keep Skill activation conditions distinct from tool input parameters. |
| Execution and dependencies | `stdio`, `npx` launch pattern, Node.js 24+, and allowed-directory restriction | Python libraries and LibreOffice are mentioned; platform compatibility is not documented in the reviewed Skill metadata | Separate transport/package/runtime/access requirements from dependencies and Skill compatibility. |
| Effects and risk | Selected tools include behavior summaries and declared MCP annotation booleans; server access is restricted to configured directories | Instructions contain workflow guardrails, not a standardized permission/effect vocabulary | Preserve source-declared hints as-is. Store any normalized risk/effect label separately and identify it as an interpretation. |
| Provenance | Source URL/path, branch, and retrieval date; exact commit is missing | Source URL/path, branch, and retrieval date; exact commit is missing | Attach provenance to individual facts where practical; at minimum preserve source, path, revision, retrieval date, and review scope per record. |
| Missing/uncertain data | Authentication, resources/prompts, and complete runtime tool schemas were not established by the reviewed sample | Formal compatibility and a link to this MCP server are not documented in the reviewed Skill source | Record the observation status and which source was checked. Do not convert missing documentation into a negative fact. |

The current MCP protocol tool definition includes a name, description, JSON Schema `inputSchema`, optional `outputSchema`, and optional annotations. The JSON sample's `input_summary` is only a human-readable summary and must not be presented as the complete interface. See the [MCP Tools specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx).

The Agent Skills specification requires `name` and `description`; it permits optional fields including `license`, `compatibility`, and `metadata`, and allows a Skill directory to bundle scripts, references, and assets. See the [Agent Skills specification](https://agentskills.io/specification).

## 3. Initial Harmonization Proposal

These are small pilot conventions to discuss, not approved ontology rules:

- **Entity types:** use three distinct values for the pilot: `mcp_server`, `mcp_tool`, and `agent_skill`.
- **Observation status:** normalize field status to `present`, `explicitly_absent`, `not_documented`, `not_checked`, `not_applicable`, or `conflicting`. Use `explicitly_absent` only when a source directly says something is absent. For `not_documented`, retain the source and review scope; do not infer non-existence.
- **Original and normalized values:** preserve the source wording/value and store any normalized label separately. For example, keep the original tool description and separately add a curator label such as `file.search`.
- **Tool effects:** keep MCP annotation flags as optional booleans (`true`, `false`, or unknown/not supplied). Do not turn an omitted flag into `false`. Keep any broader behavior label, such as `read_only` or `writes_or_mutates`, distinct from the source annotation.
- **Capability labels:** start with a small controlled list only after reviewing more examples. Candidate pilot labels include `file.read`, `file.write`, `file.search`, `spreadsheet.create`, `spreadsheet.edit`, and `spreadsheet.analyze`. Mark these as project-assigned labels, not claims made verbatim by the sources.
- **Relationships:** create a Skill-to-tool/server relationship only when a source explicitly states it. At present, no such relationship is recorded for xlsx and Filesystem.
- **Provenance:** keep the collection date separate from the source's update date. A retrieval date is not `dateModified`.

## 4. Candidate Schema.org Reuse

Schema.org can provide general, widely understood metadata terms, but it does not appear to describe every MCP protocol field or Skill activation rule. Proposed matches below are tentative:

| Project concept | Candidate Schema.org term | Fit and boundary |
|---|---|---|
| Common human-readable metadata | `schema:name`, `schema:description` | Good fit for server, tool, and Skill labels/descriptions. |
| MCP server software | `schema:SoftwareApplication`; potentially `schema:softwareVersion`, `schema:runtimePlatform`, `schema:softwareRequirements`, `schema:license` | Reasonable starting point for the software package. Deployment/transport and Registry-specific package arguments still need project-specific terms. A remote service/endpoint may need separate representation; revisit after sampling a contrasting remote server. |
| Agent Skill package | `schema:CreativeWork`; `schema:license` | A Skill is a packaged instructional artifact with metadata and Markdown content. Do not classify every Skill as `schema:HowTo`; that type may fit a procedural part of a Skill, not necessarily the whole package. |
| MCP server's offered operations | Possible link through `schema:potentialAction` to an action-shaped capability | Exploratory only. Keep a local `MCPTool` concept for the MCP tool definition, including `inputSchema`, `outputSchema`, and MCP annotations; validate the semantics before asserting equivalence to `schema:Action`. |
| Capability concepts and protocol properties | Project-specific terms such as `acg:Capability`, `acg:providesCapability`, `acg:exposesTool`, `acg:activationCondition`, `acg:transport`, and `acg:inputSchema` | Schema.org has useful broad terms, but these exact relations and protocol structures need precise local definitions rather than forcing a weak mapping. |

Schema.org defines `SoftwareApplication` as software and provides version/runtime/dependency properties; `CreativeWork` is a broad type that includes software and other works. Its `potentialAction` property describes a supported, idealized action, which makes it worth testing for discovery but not enough to replace an MCP-specific tool model. See [SoftwareApplication](https://schema.org/SoftwareApplication), [CreativeWork](https://schema.org/CreativeWork), [softwareRequirements](https://schema.org/softwareRequirements), [softwareVersion](https://schema.org/softwareVersion), and [Schema.org Actions](https://legal.schema.org/docs/actions.html).

## 5. Draft Competency Questions

These 12 questions refine the topics already listed in `docs/notes.md`; current sample coverage varies:

1. Which MCP servers offer file-system capabilities?
2. Which tools can search for files, and what search patterns can they accept?
3. Which tools read files, and which tools create, overwrite, or otherwise modify data?
4. What inputs and output structures does each MCP tool declare?
5. Which tool effects or safety hints are explicitly declared by the server?
6. How is an MCP server launched, and what transport, runtime, access, or authentication requirements are documented?
7. Which Agent Skills support spreadsheet tasks and file formats?
8. Under what conditions should a Skill be activated, and which tasks does it exclude?
9. What dependencies and supporting files does a Skill declare or reference?
10. Which resources and prompts does an MCP server expose?
11. Is a Skill explicitly associated with an MCP server or tool, and what source supports that association?
12. Which source, revision, and retrieval date support each discovered field or capability?

Questions 2-9 and 12 are at least partly addressable within the pilot. Question 1 is answerable for the single sampled server, but not generalizable to the ecosystem. Questions 10 and 11 are not answerable from the reviewed sources.

## 6. Decisions to Get from the Meeting

- Agree whether Filesystem + xlsx are a suitable first pair and assign one contrasting MCP server and one additional Skill for the next sample.
- Decide whether the next extraction should record all documented Filesystem tools or retrieve the live `tools/list` response and full JSON Schemas.
- Agree on the observation-status values and the rule that source-declared facts, curator labels, and inferred relationships remain distinguishable.
- Review the proposed Schema.org mappings, especially the boundary between `SoftwareApplication`, `CreativeWork`, and MCP-specific `MCPTool`/`Capability` concepts.
- Split responsibilities with the teammate: source sampling and field/value inventory versus vocabulary alignment and competency-question validation.

**Target outcome:** leave the meeting with an agreed pilot corpus, ownership of the next sampling tasks, and a provisional vocabulary direction—not a frozen ontology or production system.
