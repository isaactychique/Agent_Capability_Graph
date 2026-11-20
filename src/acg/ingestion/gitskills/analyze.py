"""Full GitSkills analysis. Run from the repository root after the verified core download.

python -m src.acg.ingestion.gitskills.analyze --cache /path/to/cache
Large intermediate files stay in the cache; aggregate CSVs go to reports/gitskills.
No completeness filter is applied before measuring the population.
"""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import duckdb
from .collect import REVISION, write_json
from .parser import PARSER_VERSION, parse_content, field_state, fields

COLUMNS = ["file_sha", "repo_full_name", "path", "parse_status", "content_sha256",
           "name", "name_state", "description", "description_state", "skill_license",
           "license_state", "upstream_frontmatter_valid", "upstream_name",
           "upstream_description"]


def sql_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def export(db, query, target):
    temporary = target.with_suffix(target.suffix + ".tmp")
    db.execute(f"COPY ({query}) TO {sql_string(temporary)} (HEADER, DELIMITER ',')")
    temporary.replace(target)


def parse_part(db, source, target):
    csv_path = target.with_suffix(".csv")
    stats_path = target.with_suffix(".json")
    if csv_path.exists() and stats_path.exists():
        previous = json.loads(stats_path.read_text())
        if previous.get("parser_version") == PARSER_VERSION:
            print(f"Reuse parsed {source.name}", flush=True)
            return previous
    counter = Counter()
    count = 0
    temporary = csv_path.with_suffix(".csv.tmp")
    query = """SELECT file_sha, repo_full_name, path, content, content_fetched,
               frontmatter_valid, name, description FROM read_parquet(?)
               WHERE dedup_primary = 1"""
    reader = db.cursor()
    reader.execute(query, [str(source)])
    with temporary.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(COLUMNS)
        while batch := reader.fetchmany(256):
            for sha, repo, path, content, fetched, valid, old_name, old_desc in batch:
                status, meta, sha256 = parse_content(content, sha, fetched)
                name_state, name = field_state(meta, "name", status)
                desc_state, description = field_state(meta, "description", status)
                license_state, license_value = field_state(meta, "license", status)
                writer.writerow([sha, repo, path, status, sha256, name, name_state,
                                 description, desc_state, license_value, license_state,
                                 valid, old_name, old_desc])
                counter.update(fields(meta))
                count += 1
            if count % 25088 == 0:
                print(f"Parsing {source.name}: {count:,} representatives", flush=True)
    reader.close()
    temporary.replace(csv_path)
    result = {"parser_version": PARSER_VERSION, "representatives": count,
              "fields": [list(key) + [n] for key, n in sorted(counter.items())]}
    write_json(stats_path, result)
    print(f"Parsed {source.name}: {count:,} representatives", flush=True)
    return result


def analyze(cache, output):
    info = json.loads((cache / "manifest.json").read_text())
    if info["revision"] != REVISION or not info.get("verified_at"):
        raise ValueError("Run the pinned collector and finish file verification first")
    for item in info["files"]:
        if (cache / item["path"]).stat().st_size != item["size"]:
            raise ValueError(f"Incomplete file: {item['path']}")
    output.mkdir(parents=True, exist_ok=True)
    derived = cache / f"parsed-v{PARSER_VERSION}"
    derived.mkdir(exist_ok=True)
    db = duckdb.connect(str(derived / "analysis.duckdb"))
    db.execute("SET memory_limit='2GB'")
    db.execute("SET threads=2")
    db.execute("SET preserve_insertion_order=false")
    db.execute(f"SET temp_directory={sql_string(derived / 'spill')}")
    files = sorted(cache.glob("data/artifacts/*.parquet"))
    artifact_glob = str(cache / "data/artifacts/*.parquet")
    db.execute(f"""CREATE OR REPLACE TABLE occurrences AS SELECT
        repo_full_name, path, filename, location_class, file_sha, dedup_primary,
        content_fetched, content_sha_ok, frontmatter_valid,
        name AS upstream_name, description AS upstream_description,
        has_scripts, has_references, composition_fetched, composition_truncated
        FROM read_parquet({sql_string(artifact_glob)})""")
    print("Loaded occurrence columns (without bodies)", flush=True)
    db.execute("""CREATE OR REPLACE TABLE content_groups AS SELECT file_sha,
        count(*) AS occurrences, count(*) FILTER(WHERE dedup_primary=1) AS representatives
        FROM occurrences GROUP BY file_sha""")
    ambiguous = db.execute("SELECT count(*) FROM content_groups WHERE representatives<>1 OR file_sha IS NULL").fetchone()[0]
    if ambiguous:
        export(db, "SELECT * FROM content_groups WHERE representatives<>1 OR file_sha IS NULL", output / "representative_anomalies.csv")
        raise ValueError(f"{ambiguous} content groups lack exactly one representative; inspect anomalies")
    counter = Counter()
    for file in files:
        part = parse_part(db, file, derived / file.stem)
        counter.update({tuple(row[:4]): row[4] for row in part["fields"]})
    column_sql = ",".join(sql_string(x) + ":'VARCHAR'" for x in COLUMNS)
    db.execute(f"""CREATE OR REPLACE TABLE contents AS SELECT * FROM read_csv(
        {sql_string(derived / 'part-*.csv')}, header=true, columns={{{column_sql}}},
        auto_detect=false, delim=',', quote='"', escape='"', new_line='\\r\\n',
        max_line_size=2000000)""")
    db.execute(f"CREATE OR REPLACE TABLE repos AS SELECT * FROM read_parquet({sql_string(cache / 'data/repos/*.parquet')})")
    # These joins carry text metadata by hash, and repository metadata by repository.
    db.execute("""CREATE OR REPLACE VIEW joined AS SELECT o.*, c.parse_status,
        c.name, c.name_state, c.description, c.description_state, c.skill_license,
        c.license_state FROM occurrences o LEFT JOIN contents c USING(file_sha)""")
    metrics = {}
    for name, query in {
        "occurrences": "SELECT count(*) FROM occurrences",
        "unique_contents": "SELECT count(*) FROM content_groups",
        "representative_rows": "SELECT count(*) FROM contents",
        "repositories_table": "SELECT count(*) FROM repos",
        "repositories_in_artifacts": "SELECT count(DISTINCT repo_full_name) FROM occurrences",
        "exact_SKILL_md_occurrences": "SELECT count(*) FROM occurrences WHERE filename='SKILL.md'",
        "parsed_frontmatter_contents": "SELECT count(*) FROM contents WHERE parse_status='parsed'",
        "nonrepresentative_rows": "SELECT count(*) FROM occurrences WHERE dedup_primary<>1",
        "both_name_description_contents": "SELECT count(*) FROM contents WHERE name_state='present' AND description_state='present'",
        "unmatched_content_rows": "SELECT count(*) FROM joined WHERE parse_status IS NULL",
    }.items():
        metrics[name] = db.execute(query).fetchone()[0]
    assert metrics["unique_contents"] == metrics["representative_rows"]
    assert metrics["unmatched_content_rows"] == 0
    metrics["excess_copy_occurrences"] = metrics["occurrences"] - metrics["unique_contents"]
    with (output / "population.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["metric", "count"])
        writer.writerows(metrics.items())
    export(db, "SELECT parse_status,count(*) AS unique_contents FROM contents GROUP BY 1 ORDER BY 2 DESC", output / "parse_status.csv")
    union = []
    for unit, table in [("unique_content", "contents"), ("occurrence", "joined")]:
        for field in ("name", "description", "license"):
            union.append(f"SELECT '{unit}' AS unit,'{field}' AS field,{field}_state AS state,count(*) AS records,(SELECT count(*) FROM {table}) AS denominator FROM {table} GROUP BY 3")
    export(db, " UNION ALL ".join(union) + " ORDER BY 1,2,3", output / "field_stats.csv")
    with (output / "frontmatter_fields.csv").open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["scope", "field", "value_type", "standard_top_level", "unique_contents", "parsed_content_denominator"])
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0])):
            writer.writerow([*key, count, metrics["parsed_frontmatter_contents"]])
    export(db, "SELECT license_state,skill_license,count(*) AS unique_contents FROM contents GROUP BY 1,2 ORDER BY 3 DESC,2", output / "skill_licenses.csv")
    export(db, "SELECT license,count(*) AS repositories FROM repos GROUP BY 1 ORDER BY 2 DESC,1", output / "repository_licenses.csv")
    export(db, """SELECT CASE WHEN metadata_fetched IS DISTINCT FROM 1 THEN 'unknown_not_fetched'
        WHEN license IS NULL THEN 'null' WHEN trim(license)='' THEN 'empty'
        WHEN license='NOASSERTION' THEN 'no_assertion' ELSE 'reported_identifier' END AS state,
        count(*) AS repositories,(SELECT count(*) FROM repos) AS denominator
        FROM repos GROUP BY 1 ORDER BY 2 DESC""", output / "repository_license_states.csv")
    export(db, """SELECT r.license AS repository_license,c.license_state AS skill_license_state,
        count(*) AS occurrences FROM occurrences o LEFT JOIN repos r ON o.repo_full_name=r.full_name
        LEFT JOIN contents c USING(file_sha) GROUP BY 1,2 ORDER BY 3 DESC""", output / "license_coverage.csv")
    export(db, "SELECT filename,location_class,count(*) AS occurrences FROM occurrences GROUP BY 1,2 ORDER BY 3 DESC", output / "locations.csv")
    export(db, """SELECT dedup_primary,content_fetched,content_sha_ok,frontmatter_valid,
        count(*) AS occurrences FROM occurrences GROUP BY 1,2,3,4 ORDER BY 1,2,3,4""", output / "upstream_states.csv")
    export(db, """SELECT parse_status,upstream_frontmatter_valid,count(*) AS unique_contents,
        count(*) FILTER(WHERE name IS DISTINCT FROM nullif(regexp_replace(upstream_name,'^\\s+|\\s+$','','g'),'')) AS name_disagreements,
        count(*) FILTER(WHERE description IS DISTINCT FROM nullif(regexp_replace(upstream_description,'^\\s+|\\s+$','','g'),'')) AS description_disagreements
        FROM contents GROUP BY 1,2 ORDER BY 3 DESC""", output / "parser_comparison.csv")
    db.execute("""CREATE OR REPLACE TABLE name_conflicts AS SELECT name,count(*) AS distinct_contents,
        sum(g.occurrences) AS occurrences FROM contents c JOIN content_groups g USING(file_sha)
        WHERE name_state='present' GROUP BY name HAVING count(*)>1""")
    export(db, "SELECT * FROM name_conflicts ORDER BY distinct_contents DESC,name", output / "name_conflicts.csv")
    export(db, """SELECT c.name,c.file_sha,c.repo_full_name,c.path,c.description,c.skill_license,
        'https://api.github.com/repos/' || c.repo_full_name || '/git/blobs/' || c.file_sha AS blob_url
        FROM contents c JOIN (SELECT name FROM name_conflicts ORDER BY distinct_contents DESC,name LIMIT 20) n USING(name)
        QUALIFY row_number() OVER(PARTITION BY name ORDER BY file_sha)<=3
        ORDER BY name,file_sha""", output / "name_conflict_examples.csv")
    metrics["names_with_different_contents"] = db.execute("SELECT count(*) FROM name_conflicts").fetchone()[0]
    metrics["named_contents_in_conflicts"] = db.execute("SELECT coalesce(sum(distinct_contents),0) FROM name_conflicts").fetchone()[0]
    # Reusable full metadata, without repeating the raw Skill bodies in Git.
    for table in ("contents", "occurrences"):
        temporary = derived / f"{table}.parquet.tmp"
        db.execute(f"COPY {table} TO {sql_string(temporary)} (FORMAT PARQUET, COMPRESSION ZSTD)")
        temporary.replace(derived / f"{table}.parquet")
    write_json(output / "run_manifest.json", {
        "dataset": info["dataset"], "revision": REVISION, "parser_version": PARSER_VERSION,
        "completed_at": datetime.now(timezone.utc).isoformat(), "source_files": info["files"],
        "download_verified_at": info["verified_at"], "computed_metrics": metrics,
        "definition": "All discovered occurrences; no name/description inclusion filter. Text fields parsed once per hash; repo licenses remain separate.",
        "name_matching": "Exact string after stripping surrounding whitespace; case-sensitive, full name retained.",
        "full_metadata": [f"parsed-v{PARSER_VERSION}/contents.parquet", f"parsed-v{PARSER_VERSION}/occurrences.parquet"],
        "parser": "PyYAML CSafeLoader when available, otherwise SafeLoader; standard line-delimited frontmatter; explicit duplicate keys rejected; YAML merge overrides allowed.",
        "license_semantics": "Self-declared text, not a legal interpretation; missing repository license is not public-domain status.",
        "limits": "No sibling corpus scan, execution testing, or LLM extraction. No-frontmatter means absent declaration; parse/fetch/hash errors mean unknown. Parsed does not mean fully specification-compliant.",
    })
    db.close()
    print(json.dumps(metrics, indent=2), flush=True)
    print(f"Completed: {output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parents[4] / "reports/gitskills")
    args = parser.parse_args()
    analyze(args.cache.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
