# Full GitSkills analysis

The standalone GitSkills analysis below extends the previous 180-record sample
to all core records at a pinned dataset revision. It does not overwrite the
normalized/enriched corpus consumed by the existing graph pipeline or change
the ontology, graph selection, or capability mappings. Existing registry code
remains in `src/acg/`; the independent analysis commands run from the repository root.

This update adds only collection/processing/analysis code, offline tests,
summary CSV/JSON results, dependency pins and this README. It adds no raw
GitSkills corpus, full derived Parquet tables, slides, meeting reports,
AI review scores, capability-extraction drafts, or SkillsBench experiments.
Existing source snapshots already used by the graph pipeline are preserved.

Start with `reports/gitskills/population.csv`, then `field_stats.csv`,
`repository_license_states.csv`, `frontmatter_fields.csv` and `name_conflicts.csv`.
These are aggregate results and selected examples, not the complete row-level
metadata dataset. The full reusable tables are regenerated outside Git.

| Code | Purpose |
| --- | --- |
| `src/acg/ingestion/gitskills/collect.py` | Download and verify the pinned core tables |
| `src/acg/ingestion/gitskills/parser.py` | Verify content identity and parse frontmatter with explicit states |
| `src/acg/ingestion/gitskills/analyze.py` | Join occurrence/content/repository records and export statistics |
| `tests/test_gitskills.py` | Parser and small synthetic end-to-end tests |
| `tests/test_gitskills_results.py` | Reconcile committed result totals and denominators |

## Reproduce the full analysis

Use Python 3.12 or later (this delivery was tested with Python 3.14), install
`src/acg/ingestion/gitskills/requirements.txt` in a virtual environment,
and run these commands from the repository root. Choose a cache **outside the Git
repository** with space for approximately 6.47 GB of downloads plus intermediate
tables and temporary storage.

```sh
python -m pip install -r src/acg/ingestion/gitskills/requirements.txt
python -m src.acg.ingestion.gitskills.collect --cache /path/to/gitskills-cache
python -m src.acg.ingestion.gitskills.analyze --cache /path/to/gitskills-cache
python -m unittest discover -s tests -p 'test_gitskills*.py' -v
```

The collector pins Hugging Face revision
`ebab17454a7c236f8f26b183567f1a126f42e3f8`, downloads `artifacts`, `repos`, and
`mining_runs`, and verifies each file against its LFS SHA-256. Interrupted
downloads resume. `artifact_siblings` is deliberately excluded: the full bundle
corpus is unnecessary for the current metadata questions.

The analysis reads bodies in batches, verifies the Git blob hash, and parses
one representative per content group. Per-file parsing checkpoints and a
DuckDB database stay in the cache. Re-running reuses parsing checkpoints;
change `PARSER_VERSION` whenever parser semantics change. A missing or ambiguous
representative stops the run instead of silently choosing a copy.

The cache also contains `parsed-v2/contents.parquet` (one row per distinct
content, with parsed name, description, self-declared license and states) and
`parsed-v2/occurrences.parquet` (all source locations and enrichment flags).
Join them on `file_sha`. Repository licenses remain in the source `repos` table.
These are the reusable full metadata tables; the CSV outputs below are summaries.

## Read the results

`reports/gitskills/` contains the current full-analysis outputs:

| File | Meaning |
| --- | --- |
| `run_manifest.json` | Fixed source revision, source file hashes, actual computed counts, definitions and completion time |
| `population.csv` | File occurrences, unique contents, representatives, repositories and inclusion counts |
| `parse_status.csv` | Whether unique contents were fetched, hash-verified and parsed |
| `field_stats.csv` | Name, description and self-declared license states, both by unique content and by occurrence; denominators included |
| `frontmatter_fields.csv` | Top-level and `metadata` child keys, types and frequencies among parsed contents |
| `skill_licenses.csv` | Literal license declarations inside Skill frontmatter |
| `repository_licenses.csv` | License information from the repository table, counted by repository |
| `repository_license_states.csv` | Distinguishes null, empty, NOASSERTION and reported identifiers |
| `license_coverage.csv` | Repository license versus Skill declaration availability, counted by occurrence |
| `locations.csv` | Exact filenames and location classes, without silently excluding broad search matches |
| `upstream_states.csv` | Original enrichment and validity flags, including un-enriched copies |
| `parser_comparison.csv` | Our parsing status and differences from upstream extracted name/description |
| `name_conflicts.csv` | Complete names associated with multiple verified content hashes |
| `name_conflict_examples.csv` | Up to three distinct contents for each of the 20 most varied names, with blob links |

### Interpretation

- An **occurrence** is a discovered file at a repository path. A **unique
  content** groups occurrences with the same Git blob SHA-1 (`file_sha`). Our
  `content_sha256` is a separate SHA-256 over the text bytes.
- A representative is an enrichment choice, not necessarily the original
  author. Text metadata can be shared across identical contents; bundle files,
  repository license and history cannot.
- `present`, `absent`, `empty`, `invalid_type`, and `unknown` are separate
  states. Missing/unverified text or unparseable YAML is `unknown`. A verified
  file with no frontmatter has no frontmatter declarations (`absent`). This
  does not claim that its body contains no useful information.
- A malformed apparent opening delimiter, an unclosed block or invalid YAML
  is `unknown`, not evidence that the author omitted each field.
- `parsed` means a YAML mapping was parsed, **not** full Agent Skills compliance.
  Explicit duplicate keys are rejected; standard YAML merge overrides are
  supported. Top-level non-string keys are reported separately.
- Name grouping is case-sensitive on the full string after trimming outside
  whitespace. Different hashes establish different bytes, not different
  capabilities. Review the text before making a semantic claim.
- License values are literal declarations, not normalized legal conclusions.
  Skill license, repository license and the dataset's CC-BY-4.0 are distinct.
- The dataset includes broad filename search matches. Global discovery counts
  are not counts of executable, compliant, or high-quality skills.


Sources: [GitSkills](https://huggingface.co/datasets/mvaccargiu/gitskills), [Agent Skills specification](https://agentskills.io/specification).

## Download complete row-level metadata

The complete linked metadata tables are now distributed separately from the
summary reports as [GitSkills metadata v1 release assets](https://github.com/isaactychique/Agent_Capability_Graph/releases/tag/gitskills-metadata-v1).
See [download links, schema, joins and field semantics](../../docs/data/gitskills.md).
Large tables remain outside Git history. This export does not modify the graph.
