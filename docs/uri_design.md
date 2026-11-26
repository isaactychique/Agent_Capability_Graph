# URI design for the published knowledge graph

Status: w3id.org selected as the persistence service on 2026-11-25.
Proposed prefix: `https://w3id.org/agent-capability-graph`. Prefix acceptance,
public hosting and redirect deployment are still pending. The current graph still uses provisional URNs;
this document does not claim that HTTPS identifiers are already deployed.

## Current implementation

- Ontology: `urn:acg:ontology:`.
- Initial entities and observations: `urn:acg:data:`; entity IDs come from initial
  record IDs, source IDs hash source URLs, observation IDs hash entity/field/source.
- Registry entities, capabilities and assertions: `urn:acg:metadata:`; imported
  IDs encode upstream identities; canonical identity reconciliation is in SQLite.

`rdf/curated.py` and `rdf/registry.py` currently construct these identifiers.
URIs are also embedded in SQLite, selection/merge reports, overrides, generated
mappings, ontology, SHACL shapes, queries, tests and evaluation worksheets.
A prefix replacement in Turtle alone would leave inconsistent references.

## Public pattern

Let `B = https://w3id.org/agent-capability-graph`, with no trailing slash,
as the proposed base for the namespace request. This prefix has not been
registered by this project; its availability and acceptance remain unconfirmed.

| Resource | Proposed pattern | Identity basis |
| --- | --- | --- |
| Ontology term | `B/ontology#MCPServer` | Stable vocabulary term |
| MCP server | `B/id/server/{id}` | Persisted canonical server identity |
| MCP tool | `B/id/tool/{id}` | Canonical parent server and exact tool name |
| Agent Skill | `B/id/skill/{id}` | Repository and package SKILL.md path |
| Capability concept | `B/id/capability/{id}` | Controlled action/object concept |
| Capability assertion | `B/id/assertion/{id}` | Entity, capability, source snapshot, mapping/extraction version and evidence location where applicable |
| Skill fact assertion | `B/id/skill-fact/{id}` | Entity, fact kind/value, source snapshot and text location |
| Source snapshot | `B/id/source/{id}` | Repository, path and pinned revision, or original source URL plus snapshot digest |
| Observation | `B/id/observation/{id}` | Entity, field and source snapshot |
| Corpus collection | `B/id/corpus/{id}` | Stable collection identity, separate from membership changes |

Display names are labels, not sufficient identities. A preferred name, updated
source URL, extra collector or changed sample membership must not rename a
canonical server/tool/Skill. Same-name Skills in different repositories remain
distinct. A shared repository alone never merges different MCP servers.

Assign opaque accession IDs in a persistent canonical identity registry. Existing
canonical records receive IDs once during migration; additional sources map to
those IDs after reconciliation. Deterministic hashes of identity keys can seed
new IDs, but IDs must not be recomputed from whichever source is preferred later.
The canonical registry must survive reimports rather than being recreated from
scratch on each SQLite rebuild. This persistence is a migration requirement,
not functionality already implemented.

A source revision identifies evidence, not a new Skill identity. Changed source
snapshots or assertion content can receive new evidence/assertion IDs while the
underlying resource retains its URI. Review status updates alone should not
rename the assertion. Treat URLs for GitHub blob and raw views as representations
of the same source only when repository/path/revision and content agree.

## Resolution and namespace ownership

The selected option is w3id.org, using the proposed `agent-capability-graph`
prefix. Prefix ownership must be requested and accepted; it is not assumed
available. Confirm the maintainer, retention policy and hosting before minting
final public identifiers. The namespace should not be described as active yet.

For the proposed slash resource IDs, the publication service should support
HTTP 303 redirects from `B/id/...` to descriptions. HTML and Turtle representations
can be selected through content negotiation. Ontology hash terms resolve through
the ontology document. If hosting is limited to static files without redirects,
a document-plus-fragment design is a viable alternative and should be chosen
before implementation. A GitHub `blob/...ttl` page is a file-view URL, not the
resource identity pattern.

This design follows the distinction between resources and their descriptions
and the hash/303 strategies in the W3C Interest Group Note
[Cool URIs for the Semantic Web](https://www.w3.org/TR/cooluris/).
HTTPS syntax alone does not make a URI persistent or dereferenceable: the
namespace owner must provide and maintain its resolution.

## Migration work package

1. Confirm the public base and a feasible resolution service.
2. Implement a shared identifier module and persistent canonical accession map.
3. Export a complete old-to-new mapping with resource kinds and identity bases.
4. Apply the map to SQLite canonical IDs, foreign keys and stored embedded IDs,
   manual entity overrides, evaluation worksheets and active reports. Preserve
   immutable upstream IDs and original source URLs as provenance.
5. Update ontology, shapes, query prefixes and code constants together. Keep a
   versioned mapping so previous results remain interpretable.
6. Regenerate mappings, RDF, inventory and SHACL reports from migrated inputs.
7. Check graph equivalence under the explicit IRI mapping, relationship integrity,
   unchanged competency-question answers, stable IDs after reimport and live
   HTTP resolution. A structural SHACL pass alone is insufficient.
8. Publish the ontology, descriptions and migration notes. Add old/new identity
   links only where identity equivalence is justified; do not assert that an
   entity and its documentation page are the same resource.

This work package is not executed by editing this document. Until the public
prefix is accepted and resolution is deployed, all executable queries continue
to use the current URNs.


## Preparing the w3id.org request

Proposed request metadata:

- Identifier: `agent-capability-graph` (subject to availability and acceptance).
- Purpose: persistent identifiers for the Agent Capability Graph ontology,
  canonical MCP servers/tools, Skills, capabilities and evidence assertions.
- Maintainer GitHub account: `isaactychique`; contact details must be confirmed
  before submitting the request.
- Redirect targets: pending selection and publication of HTML/Turtle descriptions.
- Status: preparation only; no fork, pull request or registration has been submitted.

The [w3id.org contribution instructions](https://github.com/perma-id/w3id.org/blob/master/README.md)
currently request a fork, an `ids/<identifier>/.htaccess` containing redirect rules
and maintainer details, validation of the rules, and a pull request. w3id.org
provides redirects, not hosting for ontology or RDF files.

Prepare the target ontology, graph and resource descriptions first. Then create
`ids/agent-capability-graph/.htaccess` in the w3id.org contribution with explicit
routes for the ontology and resource representations. Use the final serving
URLs, not placeholders or a generic redirect of every identifier to the GitHub
repository homepage. Confirm the resource/description distinction and compatible
303 or hash behavior described above. Complete and check the maintainer section,
validate the redirects, then submit the namespace request for review.

Registration does not itself migrate local SQLite/RDF identifiers. That remains
the coordinated migration work package described in this document.
