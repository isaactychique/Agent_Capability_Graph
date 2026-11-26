# Complete metadata export validation

[Download guide](../../../docs/data/gitskills.md) and
[release assets](https://github.com/isaactychique/Agent_Capability_Graph/releases/tag/gitskills-metadata-v1).

| Table | Rows |
| --- | ---: |
| contents | 1,877,981 |
| occurrences | 3,797,117 |
| repositories | 282,200 |
| metadata_fields | 6,663,894 |

All source files passed SHA-256 verification. Representative parsing states and
all field/type frequencies exactly match the existing full-corpus analysis.
No duplicate content/repository/field keys, orphan foreign keys or invalid JSON
values were found. 6,624,842 field values use ordinary JSON; 39,052 use a tagged
JSON representation to preserve YAML-specific types. The download guide explains
how to distinguish these encodings and how to interpret missing field rows.

The full existing test suite plus export tests passed: 50 tests. The export adds
no data to the canonical database or selected RDF graph. The attached tables omit
original Markdown bodies and sibling file contents, which remain upstream.

`manifest.json` contains the exact asset sizes, SHA-256 hashes, complete schemas,
pinned upstream files and export-code identity. `SHA256SUMS` also covers the
manifest. This folder contains validation metadata only; the actual large tables
are repository Release assets.
