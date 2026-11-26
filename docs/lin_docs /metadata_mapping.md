# Additional metadata: values, interpretation and proposed mapping

Snapshot: GitSkills `ebab17454a7c236f8f26b183567f1a126f42e3f8`.
This extends the existing full-corpus analysis without rerunning collection or
replacing its reports. The previous parse checkpoints retain name, description
and license but not additional values, so the new script must read and parse the
cached representative bodies to compute those values. Exactly the same parser is
used; every selected field/type frequency and all parse-status totals reconcile.

**Unit:** one representative per exact Git blob hash. Field presence percentages
use 1,665,672 parsed mappings, not all 1,877,981 hashes or 3,797,117 occurrences.
Presence includes empty and invalid-type declarations; it is not valid-value coverage.
Top-level and `metadata` counts overlap and must not be added as a union.

| Field | Top-level contents | % of parsed | Findings / meaning | Proposed treatment / CQ |
|---|---:|---:|---|---|
| version | 230,017 | 13.8093% | 195,131 three-part version-like strings; 11,647 YAML numbers. Literal `1.0.0`: 113,944. A syntax match is not SemVer validation. | Preserve raw value and scope; project as schema:version after review. Numeric parsing may lose author formatting. CQ12. |
| allowed-tools | 174,889 | 10.4996% | 124,073 strings and 50,540 lists; other types also occur. Shell lexical group: 133,297 (76.2181% of field-present contents). Groups overlap. | Existing acg:allowedTool plus source observation. A declaration does not prove safety, runtime authorization or actual use. CQ15. |
| tags | 121,798 | 7.3122% | 119,997 lists. Casefolded member groups include saas 6,859; ai 4,198; security 4,068. Do not split arbitrary prose strings into invented tags. | Preserve raw list; project string items as repeated schema:keywords. Tags are not automatically SKOS capabilities. CQ13. |
| argument-hint | 102,800 | 6.1717% | Placeholder syntax in 75,918; list values in 9,339; empty values in 1,146. Literal `[target]`: 850. | Keep source observation; optional future acg:argumentHint needs declaration. Do not populate Parameter from a hint. CQ18. |
| author | 99,374 | 5.9660% | 97,802 free-text/name strings; 1,194 mappings; attribution is self-declared. | Raw observation first. Only resolve schema:author Person/Organization if identity evidence supports it; do not make a Person from every string. CQ14. |
| user-invocable | 76,023 | 4.5641% | true 55,661; false 20,349; string-typed values 12; null 1. | Host-specific setting. Keep booleans distinct from quoted strings. Missing field is unknown in a mixed corpus. CQ17. |
| compatibility | 61,869 | 3.7144% | 57,415 strings; 27,231 fall into lexical other_text. `opencode`: 8,076; Claude mention group 14,726; Python 4,825. | Existing acg:compatibility plus observation. Lexical mention is not tested compatibility. Do not infer package dependency from any product mention. CQ16. |
| category | 79,678 | 4.7835% | Casefolded member groups: development 2,345, backend 2,032, devops 1,681. Literal strings have different counts. | Keep source taxonomy; schema:keywords is an optional search projection. Preserve original category field. CQ13. |
| disable-model-invocation | 49,436 | 2.9679% | true 37,886; false 11,534; other values 16. | Separate from user-invocable; host behavior differs. Keep observation, do not equate with security risk. CQ17. |
| model / context | 21,994 / 12,139 | 1.3204% / 0.7288% | Normalized model groups include sonnet 8,579, opus 4,218; context fork 10,203. Aliases can change meaning by host/version. | Preserve raw host-specific execution preference; defer core ontology property. |
| license | 207,600 | 12.4634% | Literal MIT 122,585; Apache-2.0 36,607; Apache 2.0 8,507. These are distinct literals. | Keep source license distinct from repository license and dataset license. No automatic legal equivalence. CQ11. |

## Why field presence is not enough

A list-valued allowed-tools is outside the string format described in the portable
Agent Skills specification but is accepted by Claude Code's documentation checked
on 26 November 2026. Thus report a **format difference**, not a universal invalid
Skill. The portable specification includes `compatibility` and experimental
`allowed-tools`, and permits extension metadata; it does not make every observed
top-level extension portable. [Agent Skills specification](https://agentskills.io/specification)

`argument-hint` is an invocation hint. `user-invocable` and
`disable-model-invocation` govern different invocation paths in Claude Code.
Interpret them only with known host context; absent values across arbitrary
repositories do not justify applying a single host's defaults.
[Claude Code skills reference](https://code.claude.com/docs/en/skills)

Schema.org offers [version](https://schema.org/version),
[keywords](https://schema.org/keywords) and [author](https://schema.org/author).
These are mapping recommendations, **not implemented ontology changes**.
The existing `MetadataObservation` already preserves raw field names, values,
status and source. Populate observations first, then add direct projections when
useful. If an intermediate node is proposed, it must serve a concrete purpose:
provenance for a claim, or a genuinely identified author; avoid a node for every
string value just to increase graph size.

## Artifacts and limitations

`reports/gitskills/values-2026-11-26/` provides field totals, YAML types, all
lexical groups, top 20 serialized values per scope/field, representative examples
for the ten most frequent groups per field, and a run manifest. Group examples
carry repository, path, Git blob hash and blob API URL; truncated excerpts are
flagged. The pinned dataset remains the reproducible source even if an upstream
repository later disappears. Examples are deterministic first encountered
representatives, not a random or manually rated sample.

Lists contribute at most once per content to each casefolded member group. Tool
families and compatibility groups use transparent regexes; a negated mention can
still match. They are **exploratory distributions**, not semantic annotations.
The grouping code is `groups()` in `value_analysis.py`. No source text is executed.
`other_text` is intentionally visible and calls for human inspection. No claimed
precision/recall for lexical grouping, semantic deduplication or capability extraction.

```sh
python -m src.acg.ingestion.gitskills.value_analysis \
  --cache /path/to/existing/gitskills-cache \
  --output reports/gitskills/values-2026-11-26
```

Source files were previously LFS-hash verified by the collector; this extension
checks pinned revision and sizes and recomputes representative Git blob hashes.
It does not independently rehash every Parquet file. Its aggregate results exactly
reconcile with the prior verified analysis. No full row-level corpus is committed.
