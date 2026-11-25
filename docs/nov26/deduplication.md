# Answer to the deduplication question

We group source occurrences by `file_sha`, the **Git blob SHA-1**, not Skill name,
repository, or a semantic fingerprint. The parser recomputes:

```text
SHA1(b"blob " + ASCII(byte_length) + b"\0" + UTF8(content))
```

Consequently adding one newline, changing LF to CRLF, or changing any byte
creates a different content identity. This is exact-content deduplication;
near-duplicates, minor edits and semantically equivalent instructions remain
separate. Conversely identical SKILL.md content does not prove identical Skill
packages: scripts, references, repository licenses and execution environments can
differ. Those must remain tied to their occurrence/package, not copied by hash.

The pinned baseline has 3,797,117 occurrences, 1,877,981 distinct SHA groups and
1,919,136 excess copy occurrences. There are 42 representative hash mismatches;
1,877,939 representatives passed the byte-hash check, including verified texts
with malformed/no frontmatter. Mismatches remain visible with unknown field
states rather than silently entering trusted metadata statistics. The independent
SHA-256 content digest is stored for verified texts; it does not turn the scheme
into semantic deduplication. SHA-1 has known collision limitations, so this is not
a mathematical uniqueness guarantee against adversarial data.

We have **not measured semantic deduplication precision/recall**, because we have
no independently labeled duplicate/nonduplicate pairs. Hash verification measures
consistency with stored bytes, not semantic correctness. A separate future study
could compare line-ending/terminal-newline normalization and near-duplicate
methods on manually labeled pairs, with false merges reported before changing
entity identity. Do not collapse whitespace globally: indentation, code blocks
and executable examples can carry meaning.

An executable sensitivity check (`test_hash_is_byte_identity`) compares identical
text, one appended newline and CRLF substitution. It proves the implementation's
boundary; it is not a corpus-wide estimate of how many near-duplicates exist.

The current selected graph has one exact-name collision: `mcp-builder` under
Microsoft and Anthropic identities (CQ20). This establishes two source identities,
not different behavior. The original GitSkills `name_conflict_examples.csv`
separately provides different content hashes; differing bytes alone also do not
establish different capabilities.
