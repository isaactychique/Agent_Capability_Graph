import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import duckdb
from src.acg.ingestion.gitskills.analyze import analyze, sql_string
from src.acg.ingestion.gitskills.collect import REVISION
from src.acg.ingestion.gitskills.parser import parse_content, field_state


def blob(text):
    data = text.encode()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


class Frontmatter(unittest.TestCase):
    def test_states_and_hash(self):
        self.assertEqual(parse_content(None, "unused", 0)[0], "not_fetched")
        self.assertEqual(parse_content("text", "wrong", 1)[0], "hash_mismatch")
        self.assertEqual(parse_content("text", blob("text"), 1)[0], "no_frontmatter")
        self.assertEqual(field_state({}, "name", "not_fetched")[0], "unknown")
        self.assertEqual(field_state({}, "name", "no_frontmatter")[0], "absent")
        self.assertEqual(field_state({"name": []}, "name", "parsed")[0], "invalid_type")
        self.assertEqual(field_state({"name": " "}, "name", "parsed")[0], "empty")
        malformed = "---name: example\n---\n"
        self.assertEqual(parse_content(malformed, blob(malformed), 1)[0], "malformed_opening")
        self.assertEqual(field_state({}, "name", "malformed_opening")[0], "unknown")

    def test_duplicate_and_merge(self):
        duplicate = "---\nname: a\nname: b\n---\n"
        self.assertEqual(parse_content(duplicate, blob(duplicate), 1)[0], "duplicate_yaml_keys")
        merged = "---\ndefaults: &d {name: old}\n<<: *d\nname: new\n---\n"
        status, meta, _ = parse_content(merged, blob(merged), 1)
        self.assertEqual((status, meta["name"]), ("parsed", "new"))

    def test_crlf_and_nonmapping(self):
        content = "\ufeff---\r\nname: group/name\r\nlicense: MIT\r\n---\r\nbody"
        status, meta, _ = parse_content(content, blob(content), 1)
        self.assertEqual((status, meta["name"]), ("parsed", "group/name"))
        text = "---\n- a\n---\n"
        self.assertEqual(parse_content(text, blob(text), 1)[0], "non_mapping_yaml")


class EndToEnd(unittest.TestCase):
    def test_copies_licenses_and_denominators(self):
        with tempfile.TemporaryDirectory() as root:
            cache = Path(root)
            for name in ("artifacts", "repos"):
                (cache / "data" / name).mkdir(parents=True)
            db = duckdb.connect()
            db.execute("""CREATE TABLE a(repo_full_name VARCHAR,path VARCHAR,filename VARCHAR,
                location_class VARCHAR,file_sha VARCHAR,dedup_primary INTEGER,content_fetched INTEGER,
                content_sha_ok INTEGER,frontmatter_valid INTEGER,name VARCHAR,description VARCHAR,
                has_scripts INTEGER,has_references INTEGER,composition_fetched INTEGER,
                composition_truncated INTEGER,content VARCHAR)""")
            texts = ["---\nname: same\ndescription: |\n  First task with \"quotes\"\n  and another line\nlicense: MIT\nmetadata: {author: someone}\n---\nA",
                     "---\nname: same\ndescription: Second task\n---\nB", "plain text"]
            for i, text in enumerate(texts):
                db.execute("INSERT INTO a VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                           ["org/one", f"{i}/SKILL.md", "SKILL.md", "standard", blob(text),
                            1, 1, 1, int(i<2), "same" if i<2 else None,
                            ["First task", "Second task", None][i], 0, 0, 1, 0, text])
            db.execute("INSERT INTO a SELECT 'org/two',path,filename,location_class,file_sha,0,0,NULL,NULL,NULL,NULL,NULL,NULL,0,0,NULL FROM a WHERE path='0/SKILL.md'")
            artifact = cache / "data/artifacts/part-00000.parquet"
            db.execute(f"COPY a TO {sql_string(artifact)} (FORMAT PARQUET)")
            repo = cache / "data/repos/part-00000.parquet"
            db.execute(f"COPY (SELECT 'org/one' AS full_name,'MIT' AS license,1 AS metadata_fetched UNION ALL SELECT 'org/two','Apache-2.0',1) TO {sql_string(repo)} (FORMAT PARQUET)")
            db.close()
            (cache / "manifest.json").write_text(json.dumps({"dataset":"fixture", "revision":REVISION,
                "verified_at":"fixture", "files":[{"path":str(x.relative_to(cache)),"size":x.stat().st_size} for x in (artifact,repo)]}))
            output = cache / "results"
            analyze(cache, output)
            metrics = json.loads((output / "run_manifest.json").read_text())["computed_metrics"]
            self.assertEqual((metrics["occurrences"],metrics["unique_contents"]), (4,3))
            self.assertEqual(metrics["names_with_different_contents"], 1)
            self.assertTrue((cache / "parsed-v2/contents.parquet").exists())
            with (output / "field_stats.csv").open() as stream:
                rows = list(csv.DictReader(stream))
            row = next(x for x in rows if x["unit"]=="occurrence" and x["field"]=="description" and x["state"]=="present")
            self.assertEqual((row["records"],row["denominator"]), ("3","4"))
            with (output / "license_coverage.csv").open() as stream:
                licenses = list(csv.DictReader(stream))
            self.assertTrue(any(x["repository_license"]=="Apache-2.0" and x["skill_license_state"]=="present" for x in licenses))
            # Resume produces identical metrics without reparsing.
            analyze(cache, output)
            self.assertEqual(metrics, json.loads((output / "run_manifest.json").read_text())["computed_metrics"])


if __name__ == "__main__":
    unittest.main()
