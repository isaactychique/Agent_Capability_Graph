# Query verification, 26 November 2026

Graph baseline: `62bfd2521af9c2272c0881443889ad1c5578f687`.
6,808 triples; 10 MCP servers, 55 tools, 110 Skills; 151 capabilities and 214
assertions. The counts were computed directly, not copied from meeting notes.
Main had no later commits, no open PR and no non-main branch when inspected.
Only the previously merged PR #1 existed before this contribution.

| Query | Rows | Rows with value | Reading |
|---|---:|---:|---|
| CQ11 | 104 | 99 | 10 observations (5 populated) plus 94 direct license projections. Not 99 different licensed Skills. |
| CQ12 | 0 | 0 | Version observations not imported in this graph. |
| CQ13 | 0 | 0 | Tags/category observations not imported. |
| CQ14 | 0 | 0 | Author observations not imported. |
| CQ15 | 17 | 17 | Direct allowed-tool values; source attribution is not at field level. |
| CQ16 | 16 | 6 | 10 undocumented compatibility observations plus 5 compatibility and 1 dependency direct values. |
| CQ17 | 0 | 0 | Invocation setting observations not imported. |
| CQ18 | 0 | 0 | Argument hint observations not imported. |
| CQ19 | 111 | n/a | Capability/source rows; multiple tasks can describe one Skill. |
| CQ20 | 1 | n/a | Exact-name pair `mcp-builder`: Microsoft and Anthropic identities. |

The 100 extra Skills were imported through a different path from the original
10, so field-level observation coverage differs. Direct values are deliberately
included and explicitly marked, but a generic Skill-to-document link is not
claimed as proof of each field. The proposed next import should populate the
existing observation structure for those source values.

`query_audit.json` records graph and query SHA-256 hashes and computed counts.
CQ CSVs record all rows, including unbound fields. Row counts can change when
Isaac updates the graph; reproduce instead of asserting these counts permanently.

Validation: `python -m unittest discover -s tests -v` passed 46 tests.
Before this contribution, `test_unified_graph.py` referenced functions removed
from `acg.build` during pipeline reorganization, causing a setup error.
The minimal test repair reads the canonical database and imports selection
functions from `acg.selection`. Production pipeline behavior is unchanged.
The suite emits existing rdflib deprecation/resource warnings; there were no
remaining failures. Query fixtures are synthetic and separate from corpus data.

Additional pre-merge review reproduced all ten query exports byte-for-byte and
checked all 174 published value examples against 167 pinned source contents.
Fixed prompt substitution so template-like text in vocabulary data remains literal,
and made malformed response-status validation consistently raise ValueError.
No existing production pipeline, ontology, graph, database or mappings were changed.
