# RDF Ontology Draft for the Agent Capability Graph

**Version:** 0.1 (discussion draft)  
**Purpose:** agree on the meaning of the graph's main entities and relations before implementing SHACL shapes, SPARQL queries, or a larger dataset.

> This is a proposed application ontology, not a published or final ontology. The current `data/mini_graph.jsonld` is an exploratory graph and does not yet conform to every modeling choice below.

## 1. Scope and Modeling Principles

The graph describes discoverable MCP server software, the tools an MCP server exposes, Agent Skills, and normalized capability concepts. Its primary use is to find capabilities and explain why a resource matched.

- Keep an MCP server, each MCP tool, each Agent Skill, and each capability as separate resources.
- Preserve source-provided names, descriptions, schemas, and annotations. Store project-normalized labels separately and mark them as curator-assigned.
- Do not assert a Skill-to-server or Skill-to-tool relationship unless a reviewed source explicitly supports it.
- Do not treat an omitted value as `false`, or as proof that the capability or feature does not exist.
- Keep source provenance and review scope. A repository branch such as `main` is not a pinned revision.
- Use Schema.org for broadly shared metadata where its terms fit; use the project namespace for MCP- and Skill-specific semantics.

## 2. Namespaces

| Prefix | Namespace | Use |
|---|---|---|
| `acg:` | **To be chosen before publication.** The current prototype uses `https://example.org/agent-capability-graph#` as a placeholder only. | Project-specific classes and properties. |
| `schema:` | `https://schema.org/` | General names, descriptions, licenses, and software metadata. |
| `skos:` | `http://www.w3.org/2004/02/skos/core#` | Labels and organization of the controlled capability vocabulary. |
| `prov:` | `http://www.w3.org/ns/prov#` | General provenance terms where applicable. |
| `rdf:` / `rdfs:` / `xsd:` | W3C RDF, RDFS, and XML Schema namespaces. | RDF types, schema annotations, and datatypes. |

Do not mint public identifiers under the `example.org` placeholder. Before publication, choose a stable namespace controlled by the project or use documented local identifiers.

## 3. Core Classes

| Class | Meaning | Proposed alignment |
|---|---|---|
| `acg:MCPServer` | A software implementation that implements MCP and exposes protocol capabilities. In this project, describe the server software, not an individual client session. | `rdfs:subClassOf schema:SoftwareApplication` is a starting alignment. Model a remote endpoint/deployment separately if needed. |
| `acg:MCPTool` | An invocable operation declared by an MCP server, including its name, description, input/output schemas, and optional MCP annotations. | Keep project-specific. Do not assume it is identical to `schema:Action`. |
| `acg:AgentSkill` | A portable Skill package whose `SKILL.md` gives its name, selection description, and instructions; the package may include scripts and other resources. | `rdfs:subClassOf schema:CreativeWork` is a broad starting alignment. Do not classify every Skill as `schema:HowTo`. |
| `acg:Capability` | A normalized concept used to group resources that support similar tasks, such as file search or spreadsheet editing. | `rdfs:subClassOf skos:Concept`; use `skos:prefLabel`, `skos:altLabel`, and `skos:definition` for the vocabulary. |
| `acg:SourceDocument` | A reviewed Registry record, README, `SKILL.md`, protocol response, or other source document used as evidence. | May be aligned with `prov:Entity` and `schema:CreativeWork`. |
| `acg:CapabilityAssertion` | A statement connecting a server, tool, or Skill to a capability. It records whether the link was stated by the source or assigned during normalization. | Project-specific n-ary relation, used so the capability link itself can have provenance and an assertion method. |
| `acg:MetadataObservation` | A record that a particular field was checked and found present, explicitly absent, undocumented, unchecked, not applicable, or conflicting. | Project-specific; used only where field-level status matters. |

### Schema.org boundary

Use `schema:name` and `schema:description` across the resource types. For an MCP server, `schema:softwareVersion`, `schema:runtimePlatform`, and `schema:softwareRequirements` may fit software metadata. Use `schema:license` with a license URL or license document where available; preserve the source's original license label as well. A Skill's activation conditions, MCP tool input schemas, transport, and behavioral hints need project-specific terms.

An MCP tool could be linked to an action-shaped description with `schema:potentialAction` in a later iteration, but this draft does not claim that an MCP tool and a Schema.org Action are equivalent.

## 4. Core Relationships

| Property | Domain | Range | Meaning |
|---|---|---|---|
| `acg:exposesTool` | `acg:MCPServer` | `acg:MCPTool` | The server declares or exposes this MCP tool. |
| `acg:hasCapabilityAssertion` | `acg:MCPServer`, `acg:MCPTool`, or `acg:AgentSkill` | `acg:CapabilityAssertion` | Associates a resource with a sourced or curated capability claim. |
| `acg:assertedCapability` | `acg:CapabilityAssertion` | `acg:Capability` | The normalized capability named by the assertion. |
| `acg:basedOnSource` | `acg:CapabilityAssertion` | `acg:SourceDocument` | Source evidence used for the capability mapping. |
| `acg:documentedBy` | `acg:MCPServer`, `acg:MCPTool`, or `acg:AgentSkill` | `acg:SourceDocument` | Source in which the resource metadata was reviewed. |
| `acg:observesEntity` | `acg:MetadataObservation` | `acg:MCPServer`, `acg:MCPTool`, or `acg:AgentSkill` | Resource whose field was checked. |
| `acg:observedProperty` | `acg:MetadataObservation` | RDF property IRI | Field whose availability or value was checked. |
| `acg:reviewedSource` | `acg:MetadataObservation` | `acg:SourceDocument` | Source and scope against which the field status applies. |

A server-level capability can be stated directly through a `CapabilityAssertion`, or discovered by following `exposesTool` and a tool's capability assertion. A Skill-to-server relation is intentionally not part of the core model; add one only with evidence.

## 5. Core Properties

| Property | Applies to | Value / handling |
|---|---|---|
| `schema:name` | Server, tool, Skill, capability, source document | Preferred human-readable name or label. |
| `schema:description` | Server, tool, Skill | Preserve source wording. Do not replace it with a project-generated summary. |
| `schema:url` | Resource or source document | Canonical page when known; distinguish it from a source-citation link. |
| `schema:license` | Server or Skill | Prefer a license URL/document; preserve a literal source label separately if needed. |
| `schema:softwareVersion` | Versioned MCP server software | Literal version from a source. Do not confuse software version with Git commit/revision. |
| `schema:runtimePlatform` / `schema:softwareRequirements` | MCP server software | Runtime/platform and component requirements where the Schema.org definitions fit. |
| `acg:transport` | MCP server | Source-declared protocol transport, e.g. `stdio`; retain the original value and do not close the vocabulary prematurely. |
| `acg:inputSchema` / `acg:outputSchema` | MCP tool | Full machine-readable JSON Schemas when collected. A prose summary is not a schema. |
| `acg:readOnlyHint`, `acg:idempotentHint`, `acg:destructiveHint`, `acg:openWorldHint` | MCP tool | Optional source-declared booleans. Missing is unknown/not supplied, not `false`. |
| `acg:activationCondition` / `acg:exclusionCondition` | Agent Skill | Source wording describing when the Skill should or should not be selected. |
| `acg:dependency` / `acg:supportingFile` | Agent Skill | Initially preserve package names and relative file paths as source values; model richer dependency entities only if required. |
| `acg:sourcePath`, `acg:revision`, `acg:retrievedAt` | Source document | Repository path, exact commit/version when available, and our retrieval date. Retrieval date is not the source's modification date. |
| `acg:assertionMethod` | Capability assertion | One controlled value: `source_declared`, `curator_mapped`, or `inferred`. Mark inferred mappings explicitly; do not present them as source claims. |
| `acg:observationStatus` | Metadata observation | One of the controlled statuses defined below. |
| `acg:observedValue` | Metadata observation | Optional RDF value for an observed field; use only when a value needs field-level provenance or conflict tracking. |

## 6. Controlled Values and Missing Metadata

Use these status values consistently:

| Status | Meaning |
|---|---|
| `present` | The value was found in the reviewed source. |
| `explicitly_absent` | The source directly states that the field or feature is absent. |
| `not_documented` | The reviewed source scope does not document the field; this is not proof of absence. |
| `not_checked` | The field/source has not yet been inspected. |
| `not_applicable` | The field does not apply to this resource type. |
| `conflicting` | Reviewed sources give incompatible values; preserve both and cite each source. |

Use one observation per resource/property/source scope when recording a status. For repeated values such as dependencies or capabilities, represent each value separately. For boolean annotations, preserve `true` and `false` when declared and use status/omission to represent unknown.

## 7. Initial SHACL Design Targets

These are future validation requirements, not SHACL shapes yet:

- Every `MCPServer`, `MCPTool`, and `AgentSkill` has one `schema:name` and at least one `acg:documentedBy` source.
- Every `MCPTool` is linked from a server by `acg:exposesTool`; tool names and schemas remain separate from server metadata.
- Every `Capability` has at least one English preferred label and a definition or scope note.
- Every `CapabilityAssertion` has exactly one asserted capability and one assertion method; curated or inferred claims identify their evidence/basis.
- Every `SourceDocument` has a URL and retrieval date; revision is strongly recommended but may be unavailable.
- Every `MetadataObservation` identifies the resource, property, status, and reviewed source when the status depends on source review.

Do not use `rdfs:domain`/`rdfs:range` as if they were validation constraints. They describe vocabulary semantics and can imply types; SHACL will later express required counts, datatypes, and allowed values.

## 8. Conceptual Example

The following Turtle is illustrative. Its namespace is still a placeholder and these triples are not yet the serialization used by the project:

```turtle
@prefix acg:  <https://example.org/agent-capability-graph#> . # temporary
@prefix schema: <https://schema.org/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

acg:filesystem a acg:MCPServer, schema:SoftwareApplication ;
    schema:name "Filesystem MCP Server"@en ;
    acg:documentedBy acg:filesystemReadme ;
    acg:exposesTool acg:searchFiles .

acg:searchFiles a acg:MCPTool ;
    schema:name "search_files" ;
    acg:hasCapabilityAssertion acg:searchFilesClaim .

acg:searchFilesClaim a acg:CapabilityAssertion ;
    acg:assertedCapability acg:fileSearch ;
    acg:assertionMethod acg:curator_mapped ;
    acg:basedOnSource acg:filesystemReadme .

acg:fileSearch a acg:Capability, skos:Concept ;
    skos:prefLabel "File search"@en ;
    skos:definition "Find files or directories by pattern."@en .

acg:filesystemReadme a acg:SourceDocument, prov:Entity ;
    schema:url <https://github.com/modelcontextprotocol/servers/blob/main/src/filesystem/README.md> ;
    acg:sourcePath "src/filesystem/README.md" ;
    acg:revision "main (not commit-pinned)" ;
    acg:retrievedAt "2026-10-28"^^xsd:date .
```

## 9. Relationship to Existing Files and Open Decisions

- `data/examples.json` remains the exploratory field collection and is not itself the ontology.
- `data/mini_graph.jsonld` is an early graph sketch. It currently uses direct `acg:providesCapability` links. If the team adopts the `CapabilityAssertion` pattern above, update that file to use the assertion nodes before treating it as the canonical pilot graph.
- The `acg:` namespace must be selected before publishing data outside the project.
- Decide whether server versions are separate graph resources or properties of a server record.
- Decide whether the initial capability vocabulary is a small manually maintained SKOS concept scheme and who approves new concepts.
- Decide how to represent source-specific conflicting values and how much field-level provenance is needed in the first deliverable.
- Decide whether an MCP tool should ever be aligned with `schema:Action` or remain entirely project-specific.

## 10. References

- [RDF 1.1 Concepts](https://www.w3.org/TR/rdf-concepts/) and [RDF Schema](https://www.w3.org/TR/rdf-schema/) for graphs, classes, properties, domains, ranges, and subclass relationships.
- [JSON-LD 1.1](https://www.w3.org/TR/json-ld/) for a JSON-based RDF serialization.
- [SKOS Reference](https://www.w3.org/TR/skos-reference/) for concepts, labels, definitions, and concept schemes.
- [PROV-O](https://www.w3.org/TR/prov-o/) for provenance terms.
- [SHACL](https://www.w3.org/TR/shacl/) for future graph validation.
- [MCP Tools specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2026-07-28/server/tools.mdx) for tool names, JSON Schemas, and annotations.
- [Agent Skills specification](https://agentskills.io/specification) for Skill package/frontmatter structure.
- [Schema.org SoftwareApplication](https://schema.org/SoftwareApplication), [CreativeWork](https://schema.org/CreativeWork), and [Actions](https://legal.schema.org/docs/actions.html) for candidate alignments.
