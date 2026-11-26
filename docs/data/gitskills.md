# GitSkills row-level metadata for graph modeling

Download the complete processed tables from the repository release:

**[GitSkills metadata v1](https://github.com/isaactychique/Agent_Capability_Graph/releases/tag/gitskills-metadata-v1)**

These are complete row-level exports, not the summary CSVs in `reports/gitskills/`.
They use the same fixed GitSkills revision as the full-corpus analysis:
`ebab17454a7c236f8f26b183567f1a126f42e3f8`.
The export is independent of Isaac's canonical database, ontology, graph and
capability extraction pipeline. It changes none of those maintained artifacts.

## Downloads

| Asset | Unit and key | Contents |
| --- | --- | --- |
| [contents.parquet](https://github.com/isaactychique/Agent_Capability_Graph/releases/download/gitskills-metadata-v1/contents.parquet) | One row per `file_sha` | 1,877,981 content groups; parsed name, description, Skill license and their states, parse status, verified content SHA-256, representative source location |
| [occurrences.parquet](https://github.com/isaactychique/Agent_Capability_Graph/releases/download/gitskills-metadata-v1/occurrences.parquet) | One discovered source occurrence | 3,797,117 rows; repository, path, file hash, discovery/history metadata, representative flag and bundle-presence/collection flags |
| [repositories.parquet](https://github.com/isaactychique/Agent_Capability_Graph/releases/download/gitskills-metadata-v1/repositories.parquet) | One row per `repo_full_name` | 282,200 repositories; repository license and its state, metadata-fetch flag, owner, language and other snapshot attributes |
| [metadata_fields.parquet](https://github.com/isaactychique/Agent_Capability_Graph/releases/download/gitskills-metadata-v1/metadata_fields.parquet) | One declared field per `(file_sha, scope, field)` | 6,663,894 field rows; every parsed top-level field plus string-keyed direct children of `metadata`, with original parsed types and serialized values |
| [manifest.json](https://github.com/isaactychique/Agent_Capability_Graph/releases/download/gitskills-metadata-v1/manifest.json) | Export manifest | Exact row counts, all column names/types, validation results, source revision and file checksums |
| [SHA256SUMS](https://github.com/isaactychique/Agent_Capability_Graph/releases/download/gitskills-metadata-v1/SHA256SUMS) | Download integrity | SHA-256 for every provided data file and manifest |

Download the named assets, not GitHub's automatically generated **Source code**
archives: the large tables are release attachments and are not tracked in Git.
Parquet preserves column types and compresses repeated metadata. Python users can
read it with DuckDB or another Parquet-compatible library. No paid service is needed.

## Fields useful for modeling

- **Core description:** `name`, `description` and their extraction states.
- **Identity and evidence:** `file_sha`, verified `content_sha256`, repository and path.
- **License:** `skill_license` and `repository_license` in separate tables.
- **Version and attribution:** `version`, `author`, including nested variants.
- **Topic labels:** `tags`, `category`, and other declared extension fields.
- **Requirements and tools:** `compatibility`, `allowed-tools`, and any explicitly
  declared dependency fields present in the source. Their names and structures vary.
- **Invocation:** `argument-hint`, `user-invocable`, `disable-model-invocation`.
- **Host preferences:** `model`, `context` and other author-defined settings.
- **Nested extensions:** the complete top-level `metadata` value remains available,
  including deeper nesting and unusual non-string keys through the encoding below.

The field table includes all observed field names, not just this list. Missing
rows do not imply a negative statement. Tags, allowed tools and environment
mentions are declarations, not verified capabilities or runtime permissions.

## Joining the tables

Join occurrences to contents on **`file_sha`**. Join occurrences to repositories on
**`repo_full_name`**. Join fields to contents on **`file_sha`**. Do not join by Skill
name. The same text can occur in different repositories with different repository
licenses and bundled files. A content hash identifies text, not a whole Skill package.
The representative source in `contents` is an enrichment choice, not an origin or
ownership claim. Use `occurrences` for all known locations.

Basic DuckDB example, after downloading the assets into the current directory:

```python
import duckdb

db = duckdb.connect()
db.sql("CREATE VIEW contents AS SELECT * FROM read_parquet('contents.parquet')")
db.sql("CREATE VIEW occurrences AS SELECT * FROM read_parquet('occurrences.parquet')")
db.sql("CREATE VIEW repositories AS SELECT * FROM read_parquet('repositories.parquet')")
db.sql("CREATE VIEW fields AS SELECT * FROM read_parquet('metadata_fields.parquet')")

# One row per occurrence: keep the two license scopes separate.
db.sql('''
    SELECT o.repo_full_name, o.path, c.file_sha, c.name, c.description,
           c.skill_license, c.license_state,
           r.repository_license, r.repository_license_state
    FROM occurrences o
    JOIN contents c USING (file_sha)
    LEFT JOIN repositories r USING (repo_full_name)
    LIMIT 20
''').show()

# Metadata values stay typed and scoped. Decode value_json in the client.
db.sql('''
    SELECT c.file_sha, c.name, f.scope, f.field,
           f.value_type, f.value_state, f.value_encoding, f.value_json
    FROM contents c JOIN fields f USING (file_sha)
    WHERE f.field IN ('version', 'author', 'tags', 'category',
                     'compatibility', 'allowed-tools', 'argument-hint',
                     'user-invocable', 'disable-model-invocation')
    LIMIT 20
''').show()
```

Avoid joining all fields and all occurrences into a single permanently expanded
table unless needed: one content may have many locations and many field rows.

## Field types, scope and missing data

`scope='top'` means the original top-level key. `scope='metadata'` means a direct
child of the top-level `metadata` mapping. For example `(metadata, version)` is
separate from `(top, version)` even if both values are equal.

- `value_type` records the parsed YAML type (string, list, mapping, boolean,
  number, null, date, etc.). It does not assert schema compliance.
- `value_state='empty'` means null, an empty/whitespace-only string or an empty
  collection; otherwise `present`. False and zero remain present.
- `value_encoding='json'`: decode `value_json` with `json.loads`. String `"false"`
  stays a string, Boolean `false` stays a Boolean, and lists stay lists.
- `value_encoding='typed_json'`: the value uses a fully tagged tree to preserve
  YAML features JSON cannot represent directly. Scalar nodes have `type` and
  `value`; dates use ISO text. Mapping nodes have typed key/value `entries`.
  Collection nodes carry an `id`, and aliases/cycles use a reference node with
  that `id`. Binary scalars use base64. Do not flatten these values automatically.

The top-level `metadata` row retains the full nested value, so immediate child
rows duplicate part of that container for convenience. Do not count them as
independent author declarations. YAML comments, quoting style and exact lexical
formatting are not preserved in parsed JSON. The pinned upstream artifacts retain
the original text.

If a field row is absent, check `contents.parse_status`:

- `parsed`: the field was not declared at that scope (for string-keyed fields).
- `no_frontmatter`: the verified text has no frontmatter declaration.
- Any error status: the value is **unknown**, not absent or false.

There are 42 representative text/hash mismatches. They remain in `contents` with
`parse_status='hash_mismatch'` and have no trusted field rows. The compact basic
field states (`name_state`, `description_state`, `license_state`) retain the
existing parser's definitions, including `invalid_type`; these differ intentionally
from the general field-table presence states.

## Provenance and limits

Source: [GitSkills by mvaccargiu](https://huggingface.co/datasets/mvaccargiu/gitskills),
[pinned snapshot](https://huggingface.co/datasets/mvaccargiu/gitskills/tree/ebab17454a7c236f8f26b183567f1a126f42e3f8).
This release derives metadata from that source, verifies representative texts,
retains types and scope, and reshapes the records into linked tables. Preserve
this attribution and source revision when reusing the export. Skill and repository
license values remain source declarations; the dataset's license is a separate scope.

A source blob can be addressed as
`https://api.github.com/repos/{repo_full_name}/git/blobs/{file_sha}`.
Availability depends on the upstream repository; the pinned dataset is the
reproducible fallback. A Git blob hash is not a repository commit identifier.
Repository statistics and compatibility declarations describe the source snapshot,
not current runtime behavior.

This export has no new capability labels, human quality scores, full Markdown
bodies or sibling-file contents. Full text remains in the upstream `artifacts`
table. All 1,877,981 groups remain visible; counts are not counts of validated,
executable Skills. No data was imported into the project graph automatically.

## Reproduction and validation

Install the existing `src/acg/ingestion/gitskills/requirements.txt`, then run:

```sh
python -m src.acg.ingestion.gitskills.export_dataset \
  --cache /path/to/verified-gitskills-cache \
  --output /path/outside/repository/empty-export-directory
python -m unittest discover -s tests -p 'test_gitskills_export.py' -v
```

The existing full analysis must have produced `parsed-v2/contents.parquet` in the
cache. The exporter checks every source file SHA-256, re-parses every representative,
reconciles all field/type and parser totals, validates foreign keys and JSON,
and rejects duplicate content/repository/field keys. The release manifest records
actual results and checksums. Intermediate CSVs under `_temporary` are not assets.
