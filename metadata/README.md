# Source metadata cache

`data/` preserves the colleague's raw snapshot and machine-readable normalized/
enriched JSONL. It is an input corpus, not another project graph.
`.venv/` is the existing local Python environment.

All implementation code is in `src/acg/`. Use the root `pipeline.py` command:

```bash
metadata/.venv/bin/python pipeline.py run
```

Consultation CSVs are in `reports/registry/tables/`; source statistics are in
`reports/registry/`. To normalize the existing cache, install the optional
`src/acg/ingestion/requirements.txt` dependencies and run `python pipeline.py normalize`.

Earlier scripts and requirements forwarding files were moved to `archive/launchers/`.

The new full GitSkills analysis follows the reorganized project layout: code in
`src/acg/ingestion/gitskills/` and summary data in `reports/gitskills/`.
See [GitSkills reproduction and result definitions](../reports/gitskills/README.md).
Large raw downloads and derived Parquet tables are not stored in this directory.
