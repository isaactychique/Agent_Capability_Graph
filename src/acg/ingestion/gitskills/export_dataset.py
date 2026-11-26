"""Export complete row-level metadata for modeling without changing the project graph.

python -m src.acg.ingestion.gitskills.export_dataset --cache CACHE --output OUTPUT
The output must be outside the repository. Large Parquet files are release assets.
"""
import argparse
import base64
from collections import Counter
import csv
from datetime import date, datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import subprocess

import duckdb

from .collect import DATASET, REVISION, digest
from .parser import PARSER_VERSION, fields, parse_content, value_type

FIELD_COLUMNS = ['file_sha', 'scope', 'field', 'value_type', 'value_state',
                 'value_encoding', 'value_json']


def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip()) or (
        isinstance(value, (list, dict, set, tuple)) and len(value) == 0)


def encode_value(value):
    """Plain JSON where lossless; otherwise a fully tagged tree with alias references."""
    def plain(v, active):
        if v is None or isinstance(v, (str, bool, int)):
            return True
        if isinstance(v, float):
            return math.isfinite(v)
        if isinstance(v, (list, dict)):
            if id(v) in active:
                return False
            active = active | {id(v)}
            if isinstance(v, dict):
                return all(isinstance(k, str) and plain(x, active) for k, x in v.items())
            return all(plain(x, active) for x in v)
        return False
    if plain(value, set()):
        return 'json', json.dumps(value, ensure_ascii=False, sort_keys=True,
                                  allow_nan=False, separators=(',', ':'))
    seen = {}
    def tagged(v):
        kind = value_type(v)
        if isinstance(v, (dict, list, tuple, set)):
            if id(v) in seen:
                return {'type': 'reference', 'id': seen[id(v)]}
            ident = len(seen)
            seen[id(v)] = ident
            if isinstance(v, dict):
                return {'type': kind, 'id': ident,
                        'entries': [[tagged(k), tagged(x)] for k, x in v.items()]}
            seq = sorted(v, key=repr) if isinstance(v, set) else v
            return {'type': kind, 'id': ident, 'items': [tagged(x) for x in seq]}
        if isinstance(v, (date, datetime)):
            return {'type': kind, 'value': v.isoformat()}
        if isinstance(v, bytes):
            return {'type': kind, 'base64': base64.b64encode(v).decode('ascii')}
        if isinstance(v, float) and not math.isfinite(v):
            return {'type': kind, 'value': repr(v)}
        if v is None or isinstance(v, (str, bool, int, float)):
            return {'type': kind, 'value': v}
        raise TypeError(f'Unsupported YAML value: {type(v).__name__}')
    return 'typed_json', json.dumps(tagged(value), ensure_ascii=False,
                                    allow_nan=False, separators=(',', ':'))


def field_rows(sha, meta):
    for scope, mapping in [('top', meta), ('metadata', meta.get('metadata', {}))]:
        if not isinstance(mapping, dict):
            continue
        for key, value in mapping.items():
            if not isinstance(key, str):
                continue  # Retained within the serialized top-level metadata value.
            encoding, serialized = encode_value(value)
            yield [sha, scope, key, value_type(value),
                   'empty' if is_empty(value) else 'present', encoding, serialized]


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def copy_query(db, query, destination):
    db.execute(f'COPY ({query}) TO {sql_literal(destination)} '
               '(FORMAT PARQUET, COMPRESSION ZSTD, ROW_GROUP_SIZE 100000)')


def run(cache, output):
    root = Path(__file__).resolve().parents[4]
    cache, output = cache.resolve(), output.resolve()
    if output == root or root in output.parents:
        raise ValueError('Store large data outside the repository')
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use an empty output directory to avoid mixing releases')
    manifest = json.loads((cache / 'manifest.json').read_text())
    if manifest['dataset'] != DATASET or manifest['revision'] != REVISION:
        raise ValueError('Wrong dataset revision')
    for item in manifest['files']:
        source = cache / item['path']
        if source.stat().st_size != item['size'] or digest(source) != item['sha256']:
            raise ValueError(f'Source verification failed: {item["path"]}')
    print('Verified all source file SHA-256 hashes', flush=True)
    output.mkdir(parents=True, exist_ok=True)
    scratch = output / '_temporary'
    scratch.mkdir()
    db = duckdb.connect(str(scratch / 'export.duckdb'))
    db.execute("SET memory_limit='2GB'")
    db.execute('SET threads=1')
    db.execute('SET preserve_insertion_order=false')
    db.execute(f'SET temp_directory={sql_literal(scratch / "spill")}')
    occurrences_glob = cache / 'data/artifacts/*.parquet'
    db.execute(f'''CREATE TABLE identity_groups AS
        SELECT file_sha, count(*) AS occurrences,
        count(*) FILTER (WHERE dedup_primary=1) AS representatives
        FROM read_parquet({sql_literal(occurrences_glob)}) GROUP BY file_sha''')
    assert db.execute('SELECT count(*) FROM identity_groups WHERE file_sha IS NULL OR representatives<>1').fetchone()[0] == 0
    csv.field_size_limit(20_000_000)
    status_counts = Counter()
    type_counts = Counter()
    encoding_counts = Counter()
    new_contents = scratch / 'contents.csv'
    with new_contents.open('w', newline='', encoding='utf-8') as out:
        cw = csv.writer(out, lineterminator='\n')
        cw.writerow(['file_sha', 'parse_status', 'content_sha256'])
        for part in sorted(cache.glob('data/artifacts/*.parquet')):
            target = scratch / (part.stem + '-fields.csv')
            with target.open('w', newline='', encoding='utf-8') as stream:
                writer = csv.writer(stream, lineterminator='\n')
                writer.writerow(FIELD_COLUMNS)
                reader = db.cursor().execute('SELECT file_sha, content, content_fetched FROM read_parquet(?) WHERE dedup_primary=1', [str(part)])
                while batch := reader.fetchmany(128):
                    for sha, content, fetched in batch:
                        status, meta, content_hash = parse_content(content, sha, fetched)
                        status_counts[status] += 1
                        cw.writerow([sha, status, content_hash])
                        if status != 'parsed':
                            continue
                        for row in field_rows(sha, meta):
                            writer.writerow(row)
                            type_counts[tuple(row[1:4])] += 1
                            encoding_counts[row[5]] += 1
                reader.close()
            print(f'Parsed {part.name}: {sum(status_counts.values()):,} representatives', flush=True)
    expected = {r['parse_status']: int(r['unique_contents']) for r in csv.DictReader((root/'reports/gitskills/parse_status.csv').open())}
    assert dict(status_counts) == expected, 'Parse totals differ from existing report'
    expected_types = {(r['scope'], r['field'], r['value_type']): int(r['unique_contents'])
                      for r in csv.DictReader((root/'reports/gitskills/frontmatter_fields.csv').open())}
    assert dict(type_counts) == expected_types, 'Field/type counts differ from existing report'
    db.execute(f'''CREATE TABLE verified_contents AS SELECT * FROM read_csv(
        {sql_literal(new_contents)}, header=true, all_varchar=true, auto_detect=true,
        nullstr='', max_line_size=20000000)''')
    baseline = cache / f'parsed-v{PARSER_VERSION}/contents.parquet'
    db.execute(f'CREATE VIEW base AS SELECT * FROM read_parquet({sql_literal(baseline)})')
    assert db.execute('''SELECT count(*) FROM verified_contents v FULL OUTER JOIN base b USING(file_sha)
        WHERE v.file_sha IS NULL OR b.file_sha IS NULL
        OR v.parse_status IS DISTINCT FROM b.parse_status
        OR v.content_sha256 IS DISTINCT FROM b.content_sha256''').fetchone()[0] == 0
    copy_query(db, '''SELECT file_sha, content_sha256, parse_status,
        repo_full_name AS representative_repository, path AS representative_path,
        name, name_state, description, description_state, skill_license, license_state
        FROM base''', output / 'contents.parquet')
    copy_query(db, f'''SELECT repo_full_name, path, filename, location_class, file_sha,
        discovered_at, dedup_primary, content_fetched, content_sha_ok, frontmatter_valid,
        history_fetched, first_commit_at, last_commit_at, commit_count,
        composition_fetched, composition_truncated, has_scripts, has_references,
        sibling_count, sibling_bytes
        FROM read_parquet({sql_literal(occurrences_glob)})''', output / 'occurrences.parquet')
    copy_query(db, f'''SELECT full_name AS repo_full_name, owner, license AS repository_license,
        CASE WHEN metadata_fetched IS DISTINCT FROM 1 THEN 'unknown_not_fetched'
          WHEN license IS NULL THEN 'null' WHEN trim(license)='' THEN 'empty'
          WHEN license='NOASSERTION' THEN 'no_assertion' ELSE 'reported_identifier' END AS repository_license_state,
        metadata_fetched, stars, forks, is_fork, language, description, created_at, pushed_at
        FROM read_parquet({sql_literal(cache/'data/repos/*.parquet')})''', output / 'repositories.parquet')
    columns = ','.join(sql_literal(c)+":'VARCHAR'" for c in FIELD_COLUMNS)
    copy_query(db, f'''SELECT * FROM read_csv({sql_literal(scratch/'part-*-fields.csv')},
        header=true, auto_detect=false, columns={{{columns}}}, delim=',',
        quote='"', escape='"', max_line_size=20000000)''', output / 'metadata_fields.parquet')
    for table in ['contents', 'occurrences', 'repositories', 'metadata_fields']:
        db.execute(f'CREATE VIEW released_{table} AS SELECT * FROM read_parquet({sql_literal(output/(table+".parquet"))})')
    checks = {
        'contents': db.execute('SELECT count(*) FROM released_contents').fetchone()[0],
        'occurrences': db.execute('SELECT count(*) FROM released_occurrences').fetchone()[0],
        'repositories': db.execute('SELECT count(*) FROM released_repositories').fetchone()[0],
        'metadata_fields': db.execute('SELECT count(*) FROM released_metadata_fields').fetchone()[0],
        'duplicate_content_keys': db.execute('SELECT count(*)-count(DISTINCT file_sha) FROM released_contents').fetchone()[0],
        'duplicate_repository_keys': db.execute('SELECT count(*)-count(DISTINCT repo_full_name) FROM released_repositories').fetchone()[0],
        'orphan_occurrence_contents': db.execute('SELECT count(*) FROM released_occurrences o ANTI JOIN released_contents c USING(file_sha)').fetchone()[0],
        'orphan_occurrence_repositories': db.execute('SELECT count(*) FROM released_occurrences o ANTI JOIN released_repositories r USING(repo_full_name)').fetchone()[0],
        'orphan_fields': db.execute('SELECT count(*) FROM released_metadata_fields f ANTI JOIN released_contents c USING(file_sha)').fetchone()[0],
        'invalid_json_values': db.execute('SELECT count(*) FROM released_metadata_fields WHERE NOT json_valid(value_json)').fetchone()[0],
        'duplicate_field_keys': db.execute('SELECT coalesce(sum(n-1),0) FROM (SELECT count(*) n FROM released_metadata_fields GROUP BY file_sha,scope,field HAVING count(*)>1)').fetchone()[0],
    }
    assert checks['contents'] == 1877981 and checks['occurrences'] == 3797117 and checks['repositories'] == 282200
    assert checks['metadata_fields'] == sum(type_counts.values())
    assert all(n == 0 for k, n in checks.items() if k not in ['contents', 'occurrences', 'repositories', 'metadata_fields']), checks
    observed_types = {(scope, field, typ): n for scope,field,typ,n in db.execute('SELECT scope,field,value_type,count(*) FROM released_metadata_fields GROUP BY ALL').fetchall()}
    assert observed_types == expected_types
    schemas = {}
    for table in ['contents', 'occurrences', 'repositories', 'metadata_fields']:
        schemas[table] = [{'name': r[0], 'type': r[1]} for r in db.execute(f'DESCRIBE released_{table}').fetchall()]
    db.close()
    assets = {p.name: {'bytes': p.stat().st_size, 'sha256': digest(p)} for p in sorted(output.glob('*.parquet'))}
    result = {'dataset': DATASET, 'dataset_revision': REVISION,
              'dataset_url': f'https://huggingface.co/datasets/{DATASET}/tree/{REVISION}',
              'parser_version': PARSER_VERSION, 'export_schema_version': 1,
              'created_at': datetime.now(timezone.utc).isoformat(),
              'export_script_sha256': digest(Path(__file__)),
              'source_git_commit': subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),
              'checks': checks, 'parse_status': dict(status_counts),
              'value_encoding_counts': dict(encoding_counts), 'schemas': schemas,
              'assets': assets, 'source_files': manifest['files'],
              'limits': 'Parsed declarations, not verified behavior. All top-level fields and string-keyed metadata children. No original Markdown bodies or sibling files. Missing field rows require checking parse_status; no semantic deduplication.'}
    (output/'manifest.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    (output/'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in sorted(output.iterdir()) if p.is_file() and p.name != 'SHA256SUMS'))
    print(json.dumps({'checks': checks, 'assets': assets, 'encodings':dict(encoding_counts)},indent=2),flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    run(a.cache, a.output)
