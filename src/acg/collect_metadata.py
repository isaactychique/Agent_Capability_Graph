#!/usr/bin/env python3
"""Collect a small, revision-pinned MCP/Agent Skills metadata pilot.

Downloads selected files from the official GitHub repositories into a temporary
directory, extracts source-backed metadata, then stores field-level observations
in SQLite and exports a reviewable CSV. Downloaded files are not executed.

Run: python3 collect_metadata.py
"""

import csv
from datetime import datetime, timezone
import io
import json
import re
import sqlite3
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "interim" / "metadata.sqlite3"
CSV_PATH = ROOT / "data" / "interim" / "metadata_comparison.csv"
REVISIONS = {
    "servers": "36380287ed3b15d115b55f546617d723072b1296",
    "skills": "ca45fc496a3436251f191354091d557da31c15b5",
}
REPOSITORIES = {
    "servers": "modelcontextprotocol/servers",
    "skills": "anthropics/skills",
}


def download_sources(destination):
    """Fetch pinned GitHub snapshots, retaining only reviewed source files."""
    for key, repository in REPOSITORIES.items():
        url = f"https://codeload.github.com/{repository}/zip/{REVISIONS[key]}"
        print(f"Downloading {repository} at {REVISIONS[key][:12]} ...", flush=True)
        request = urllib.request.Request(
            url, headers={"User-Agent": "ACG-metadata-pilot/1.0"}
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            archive_data = response.read()
        with zipfile.ZipFile(io.BytesIO(archive_data)) as archive:
            for member in archive.infolist():
                parts = PurePosixPath(member.filename).parts[1:]
                if not parts or member.is_dir() or ".." in parts:
                    continue
                relative = "/".join(parts)
                if key == "servers":
                    selected = relative == "LICENSE" or relative in {
                        f"src/{server}/{name}"
                        for server in ("filesystem", "memory")
                        for name in ("package.json", "README.md", "server.ts", "index.ts")
                    }
                else:
                    selected = any(
                        relative.startswith(f"skills/{skill}/")
                        for skill in ("pdf", "docx", "xlsx")
                    )
                if selected:
                    target = destination / key / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(member))


def observation(value, status, source):
    return {"value": value, "status": status, "source": source}


def read_text(root, repo_key, relative):
    return (root / repo_key / relative).read_text(encoding="utf-8")


def evidence(repo_key, path, line=None):
    url = f"https://github.com/{REPOSITORIES[repo_key]}/blob/{REVISIONS[repo_key]}/{path}"
    return f"{url}#L{line}" if line else url


def collect(root):
    records = []
    # These two server records come from package metadata and their READMEs.
    for server in ("filesystem", "memory"):
        base = f"src/{server}/"
        package = json.loads(read_text(root, "servers", base + "package.json"))
        package_url = evidence("servers", base + "package.json")
        readme_url = evidence("servers", base + "README.md")
        fields = {
            key: observation(package.get(key), "explicit_structured", package_url)
            for key in ("name", "description", "version", "license", "repository",
                        "engines", "dependencies", "bin")
        }
        fields.update({
            "transport": observation("stdio", "document_extracted", readme_url),
            "installation": observation(
                "npx -y " + package["name"], "document_extracted", readme_url
            ),
            "authentication": observation(
                None, "not_established_from_reviewed_sources", readme_url
            ),
        })
        records.append({"id": server, "type": "MCPServer", "server": None, "fields": fields,
                        "revision": REVISIONS["servers"]})

    # Dependency examples and capability labels are curator inputs, not extracted facts.
    skill_examples = (
        ("pdf", ["pypdf", "pdfplumber", "reportlab", "pdftotext"], ["document.pdf.process"]),
        ("docx", ["docx", "pandoc"], ["document.word.process"]),
        ("xlsx", ["openpyxl", "pandas", "markitdown", "LibreOffice"],
         ["document.spreadsheet.process"]),
    )
    for skill, dependencies, capabilities in skill_examples:
        path = f"skills/{skill}/SKILL.md"
        content = read_text(root, "skills", path)
        source = evidence("skills", path)
        segments = content.split("---", 2)
        frontmatter = {}
        if len(segments) >= 3:
            for key, value in re.findall(r"(?m)^([a-z-]+):\s*(.*?)\s*$", segments[1]):
                frontmatter[key] = value.strip().strip('"\'')
        fields = {
            key: observation(value, "explicit_frontmatter", source)
            for key, value in frontmatter.items()
        }
        fields["usage_conditions"] = observation(
            frontmatter.get("description"), "explicit_frontmatter", source
        )
        fields["dependencies"] = observation(
            dependencies, "curator_examples_not_exhaustive", source
        )
        fields["supported_platform"] = observation(
            None, "not_documented_in_frontmatter", source
        )
        skill_root = root / "skills" / f"skills/{skill}"
        fields["bundled_files"] = observation(
            sorted(str(path.relative_to(skill_root)) for path in skill_root.rglob("*")
                   if path.is_file()), "repository_tree_observed", source
        )
        fields["capabilities"] = observation(
            capabilities, "inferred_curator_label", source
        )
        records.append({"id": skill, "type": "AgentSkill", "server": None,
                        "fields": fields, "revision": REVISIONS["skills"]})

    # Curated pilot selection of six tools. Signatures are extracted from source code;
    # capability labels and required-parameter lists are curator annotations.
    tool_examples = (
        ("filesystem", "read_text_file", ["path"], ["path", "head", "tail"], "file.read"),
        ("filesystem", "write_file", ["path", "content"], ["path", "content"], "file.write"),
        ("memory", "create_entities", ["entities"], ["entities"], "graph.entity.create"),
        ("memory", "search_nodes", ["query"], ["query", "limit", "observationLimit"], "graph.entity.search"),
        ("memory", "read_graph", [], ["entityTypes", "observationLimit"], "graph.read"),
        ("memory", "open_nodes", ["names"], ["names", "observationLimit"], "graph.entity.read"),
    )
    for server, name, required, parameters, capability in tool_examples:
        path = f"src/{server}/" + ("server.ts" if server == "filesystem" else "index.ts")
        source_code = read_text(root, "servers", path)
        marker = '"' + name + '",'
        if marker not in source_code:
            raise ValueError(f"Tool {name} was not found in pinned source {path}")
        start = source_code.index(marker)
        end = source_code.find("annotations:", start)
        block = source_code[start:end if end >= 0 else start + 5000]
        line = source_code[:start].count("\n") + 1
        source = evidence("servers", path, line)
        description_part = block.split("description:", 1)[-1].split("inputSchema:", 1)[0]
        description = "".join(re.findall(r'"([^"\n]*)"', description_part))
        input_schema = block.split("inputSchema:", 1)[-1].split("outputSchema:", 1)[0].strip()
        output_schema = block.split("outputSchema:", 1)[-1].split("annotations:", 1)[0].strip()
        annotations = {key: value == "true" for key, value in
                       re.findall(r"(\w+Hint): (true|false)", block)}
        fields = {
            "name": observation(name, "explicit_code", source),
            "description": observation(description, "explicit_code", source),
            "inputSchema_source": observation(input_schema, "source_code_schema_not_wire_json_schema", source),
            "outputSchema_source": observation(output_schema, "source_code_schema_not_wire_json_schema", source),
            "required_parameters": observation(required, "curator_extracted", source),
            "parameters": observation(parameters, "curator_extracted", source),
            "annotations": observation(annotations, "explicit_code", source),
            "capabilities": observation([capability], "inferred_curator_label", source),
        }
        records.append({"id": f"{server}:{name}", "type": "Tool", "server": server,
                        "fields": fields, "revision": REVISIONS["servers"]})
    return records


def persist(records):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS collection_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS entity (
                entity_id TEXT PRIMARY KEY,
                entity_type TEXT NOT NULL,
                parent_server TEXT,
                revision TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS metadata_observation (
                entity_id TEXT NOT NULL REFERENCES entity(entity_id) ON DELETE CASCADE,
                field TEXT NOT NULL,
                value_json TEXT,
                evidence_status TEXT NOT NULL,
                source_url TEXT NOT NULL,
                PRIMARY KEY (entity_id, field, source_url)
            );
        """)
        connection.execute("DELETE FROM metadata_observation")
        connection.execute("DELETE FROM entity")
        connection.execute("DELETE FROM collection_metadata")
        connection.execute(
            "INSERT INTO collection_metadata VALUES (?, ?)",
            ("collected_at", datetime.now(timezone.utc).isoformat()),
        )
        for record in records:
            connection.execute(
                "INSERT INTO entity VALUES (?, ?, ?, ?)",
                (record["id"], record["type"], record["server"], record["revision"]),
            )
            for field, item in record["fields"].items():
                connection.execute(
                    "INSERT INTO metadata_observation VALUES (?, ?, ?, ?, ?)",
                    (record["id"], field, json.dumps(item["value"], ensure_ascii=False),
                     item["status"], item["source"]),
                )
    with CSV_PATH.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["Entity ID", "Entity Type", "Field", "Value", "Evidence Status",
                         "Source", "Revision"])
        for record in records:
            for field, item in record["fields"].items():
                writer.writerow([record["id"], record["type"], field,
                                 json.dumps(item["value"], ensure_ascii=False), item["status"],
                                 item["source"], record["revision"]])


def main():
    with tempfile.TemporaryDirectory(prefix="acg_sources_") as temporary:
        source_root = Path(temporary)
        download_sources(source_root)
        records = collect(source_root)
    persist(records)
    print(f"Collected {len(records)} entities.")
    print(f"SQLite database: {DB_PATH}")
    print(f"CSV review export: {CSV_PATH}")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        raise SystemExit(f"Collection failed: {error}. Check network access and source revisions.")
