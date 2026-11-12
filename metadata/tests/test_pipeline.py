import unittest
from pathlib import Path
from unittest.mock import patch
from collectors.sources import headmatter, registry
from processing.normalize import headers, observations, repo_url, valid_url
from processing.resolve import resolve, annotate, state, key


class Parsing(unittest.TestCase):
    def test_yaml(self):
        self.assertEqual(
            headers(headmatter(b"---\r\nname: abc\r\n---\r\nbody"))[0], {"name": "abc"}
        )
        for bad in ["license: A\nlicense: B", "x: ["]:
            self.assertEqual(headers(bad)[1], "invalid_yaml")
        self.assertEqual(headers("- list")[1], "non_mapping_yaml")
        self.assertIsNone(headmatter(b"body\n---\nx\n---"))

    def test_repository_and_urls(self):
        r = {"issues": []}
        self.assertEqual(
            repo_url(
                {"repo": "https://a.example", "github_url": "https://b.example"}, r
            ),
            "https://a.example",
        )
        self.assertIn("conflict:repository_url", r["issues"])
        self.assertFalse(valid_url("https:// bad"))
        self.assertFalse(valid_url("file:///local"))
        self.assertTrue(valid_url("https://a.example/repo"))

    def test_absence(self):
        r = {
            "field_states": {"x": "unknown", "y": "not_applicable"},
            "z": False,
            "list": [],
        }
        self.assertEqual(
            [state(r, k) for k in ["x", "y", "z", "w", "list"]],
            ["unknown", "not_applicable", "present", "missing", "present"],
        )

    def test_repeated_cursor(self):
        with patch(
            "collectors.sources.snapshot",
            return_value={"data": {"metadata": {"nextCursor": "repeat"}}},
        ):
            with self.assertRaisesRegex(ValueError, "Repeated registry cursor"):
                registry(3)


class ReleaseEvidence(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.obs = observations()
        cls.entities, cls.events = resolve(cls.obs)

    def test_foreign_keys_and_sources(self):
        self.assertEqual(len({r["observation_id"] for r in self.obs}), len(self.obs))
        servers = {key(r) for r in self.entities if r["entity_type"] == "server"}
        self.assertTrue(
            all(
                r["server_id"] in servers
                for r in self.entities
                if r["entity_type"] == "tool"
            )
        )
        self.assertTrue(all(Path(r["raw_file"]).exists() for r in self.obs))
        self.assertTrue(all(r["source_url"].startswith("https://") for r in self.obs))

    def test_tools_and_annotations(self):
        tools = {r["name"]: r for r in self.entities if r["entity_type"] == "tool"}
        self.assertEqual(tools["read_text_file"]["required_parameters"], ["path"])
        self.assertEqual(tools["edit_file"]["required_parameters"], ["path", "edits"])
        self.assertEqual(tools["list_allowed_directories"]["required_parameters"], [])
        for r in tools.values():
            self.assertTrue(
                r["description"] and r["input_schema"] and r["output_schema"]
            )
            self.assertIn(r["source_revision"], r["source_url"])
        annotations = annotate(self.entities)
        self.assertTrue(
            all(r["tool_id"] in {key(t) for t in tools.values()} for r in annotations)
        )
        self.assertTrue(
            all(r["requires_authentication"] == "unknown" for r in annotations)
        )

    def test_release_dedup(self):
        skills = [r for r in self.entities if r["entity_type"] == "skill"]
        named = [r for r in skills if r["name"] == "skill-creator"]
        self.assertGreater(len({r["content_hash"] for r in named}), 1)
        self.assertEqual(len(set(map(key, named))), len(named))
        app = [r for r in skills if r["name"] == "applicationinsights-web-ts"]
        self.assertEqual(len({r["content_hash"] for r in app}), 1)
        self.assertGreater(len(app), 1)
        rejected = [r for r in self.obs if r["disposition"] != "accepted"]
        self.assertTrue(all(not r["name"] or not r["description"] for r in rejected))

    def test_versions(self):
        server = next(r for r in self.entities if r["name"] == "ad.getle/leads")
        revisions = {r["version"] for r in self.obs if key(r) == key(server)}
        self.assertGreater(len(revisions), 1)
        self.assertTrue(server["is_latest"])
