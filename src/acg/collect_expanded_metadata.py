#!/usr/bin/env python3
"""Collect a pinned, multi-source MCP server and Agent Skills sample.

GitHub sources are resolved to commit SHAs at run time. MCP tool summaries are
curator-transcribed from each pinned README; Skill metadata and complete Skill
directories are downloaded from their pinned repository snapshots. No downloaded
code is executed.
"""

import csv
import io
import json
import re
import sqlite3
import subprocess
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "data" / "sources" / "expanded_sources.json"
DB_PATH = ROOT / "data" / "interim" / "metadata.sqlite3"
CSV_PATH = ROOT / "data" / "interim" / "metadata_comparison.csv"
README_DIR = ROOT / "data" / "raw" / "downloads" / "mcp_readmes"
SKILL_ARCHIVE_DIR = ROOT / "data" / "raw" / "downloads" / "skill_packages"
API_ROOT = "https://api.github.com"
RAW_ROOT = "https://raw.githubusercontent.com"
USER_AGENT = "Agent-Capability-Graph-Research/1.0"
MAX_SKILL_BYTES = 20 * 1024 * 1024


def request_bytes(url, accept="application/vnd.github+json"):
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": accept}
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return response.read()
    except urllib.error.HTTPError as error:
        raise RuntimeError(f"GitHub request failed ({error.code}) for {url}") from error


def request_json(url):
    return json.loads(request_bytes(url).decode("utf-8"))


def github_snapshot(repository):
    result = subprocess.run(
        ["git", "ls-remote", f"https://github.com/{repository}.git", "HEAD"],
        check=True, capture_output=True, text=True, timeout=90,
    )
    revision = result.stdout.split()[0]
    branch = "HEAD"
    try:
        tree_data = request_json(
            f"{API_ROOT}/repos/{repository}/git/trees/{revision}?recursive=1"
        )
        if tree_data.get("truncated"):
            raise RuntimeError(f"GitHub returned a truncated file tree for {repository}")
        files = {item["path"] for item in tree_data.get("tree", [])
                 if item.get("type") == "blob"}
    except RuntimeError as error:
        # GitHub's unauthenticated tree API is rate limited. Reuse the complete
        # local package archive and README snapshots if this is a refresh run.
        if "(403)" not in str(error):
            raise
        files = set()
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        for server in manifest["mcp_servers"]:
            if server["repository"] == repository:
                local_readme = README_DIR / f"{server['id']}.md"
                if not local_readme.is_file():
                    raise RuntimeError(f"Rate limited and no cached README for {server['id']}")
                files.add(server["readme"])
        for skill in manifest["agent_skills"]:
            if skill["repository"] != repository:
                continue
            archive_path = SKILL_ARCHIVE_DIR / f"{repository.replace('/', '__')}__{skill['id']}.zip"
            if not archive_path.is_file():
                raise RuntimeError(f"Rate limited and no cached Skill package for {skill['id']}")
            package_root = str(PurePosixPath(skill["skill_md"]).parent)
            files.add(skill["skill_md"])
            with zipfile.ZipFile(archive_path) as archive:
                for name in archive.namelist():
                    if name.startswith(skill["id"] + "/"):
                        suffix = name[len(skill["id"]) + 1:]
                        if suffix:
                            files.add(str(PurePosixPath(package_root) / suffix))
    return {"repository": repository, "branch": branch, "revision": revision,
            "files": files}


def github_raw(snapshot, path):
    return request_bytes(
        f"{RAW_ROOT}/{snapshot['repository']}/{snapshot['revision']}/{path}",
        accept="application/vnd.github.raw",
    )


def source_url(snapshot, path):
    return (f"https://github.com/{snapshot['repository']}/blob/"
            f"{snapshot['revision']}/{path}")


def field(value, status, source):
    return {"value": value, "status": status, "source": source}


def parse_frontmatter(markdown):
    pieces = markdown.split("---", 2)
    if len(pieces) < 3:
        raise ValueError("SKILL.md has no YAML frontmatter delimiters")
    lines = pieces[1].splitlines()
    result = {}
    current_key = None
    block_value = []
    block_mode = None

    def finish_block():
        if current_key and block_value:
            separator = " " if block_mode == ">" else "\n"
            result[current_key] = separator.join(part.strip() for part in block_value).strip()

    for line in lines:
        match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if match:
            finish_block()
            current_key = match.group(1)
            raw_value = match.group(2).strip()
            block_value = []
            if raw_value in (">", ">-", ">+", "|", "|-", "|+"):
                block_mode = raw_value[0]
            else:
                block_mode = None
                result[current_key] = raw_value.strip('"\'')
        elif current_key and line.startswith((" ", "\t")) and block_mode:
            block_value.append(line.strip())
    finish_block()
    return result


def safe_package_path(path):
    pure = PurePosixPath(path)
    if pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Unsafe path in repository tree: {path}")
    return pure


def collect_skill_package(skill, snapshot):
    skill_path = skill["skill_md"]
    if skill_path not in snapshot["files"]:
        raise FileNotFoundError(f"Missing Skill file: {snapshot['repository']}:{skill_path}")
    package_root = str(PurePosixPath(skill_path).parent)
    members = sorted(path for path in snapshot["files"]
                     if path.startswith(package_root + "/") or path == skill_path)
    archive_path = SKILL_ARCHIVE_DIR / f"{snapshot['repository'].replace('/', '__')}__{skill['id']}.zip"
    if archive_path.exists():
        return members, archive_path
    archive_buffer = io.BytesIO()
    total_size = 0
    with zipfile.ZipFile(archive_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative_path in members:
            safe_package_path(relative_path)
            payload = github_raw(snapshot, relative_path)
            total_size += len(payload)
            if total_size > MAX_SKILL_BYTES:
                raise ValueError(
                    f"Skill package {skill['id']} exceeds {MAX_SKILL_BYTES // (1024 * 1024)} MB"
                )
            archive_name = PurePosixPath(skill["id"]) / PurePosixPath(relative_path).relative_to(package_root)
            archive.writestr(str(archive_name), payload)
    SKILL_ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path.write_bytes(archive_buffer.getvalue())
    return members, archive_path


def collect(manifest):
    repositories = sorted({item["repository"] for item in
                           manifest["mcp_servers"] + manifest["agent_skills"]})
    snapshots = {}
    for repository in repositories:
        print(f"Resolving {repository} ...", flush=True)
        snapshots[repository] = github_snapshot(repository)

    records = []
    readmes = {}
    README_DIR.mkdir(parents=True, exist_ok=True)
    for server in manifest["mcp_servers"]:
        snapshot = snapshots[server["repository"]]
        readme_path = server["readme"]
        if readme_path not in snapshot["files"]:
            raise FileNotFoundError(f"Missing MCP README: {server['repository']}:{readme_path}")
        local_readme = README_DIR / f"{server['id']}.md"
        readme_bytes = local_readme.read_bytes() if local_readme.is_file() else github_raw(snapshot, readme_path)
        readme = readme_bytes.decode("utf-8", errors="replace")
        # Every selected tool name must be present in the source snapshot used as evidence.
        missing_tools = [name for name, _ in server["tools"] if name.lower() not in readme.lower()]
        if missing_tools:
            raise ValueError(
                f"Tool names absent from pinned README for {server['id']}: {missing_tools}"
            )
        local_readme.write_bytes(readme_bytes)
        readmes[server["id"]] = local_readme
        readme_url = source_url(snapshot, readme_path)
        repo_url = f"https://github.com/{server['repository']}"
        fields = {
            "name": field(server["name"], "curator_transcribed_from_readme", readme_url),
            "description": field(server["description"], "curator_transcribed_from_readme", readme_url),
            "repository": field(repo_url, "repository_metadata", readme_url),
            "readme_path": field(readme_path, "repository_tree_observed", readme_url),
            "documented_tool_count": field(len(server["tools"]), "selected_documented_tools", readme_url),
        }
        records.append({"id": server["id"], "type": "MCPServer", "server": None,
                        "fields": fields, "revision": snapshot["revision"]})
        for tool_name, description in server["tools"]:
            tool_fields = {
                "name": field(tool_name, "explicit_tool_name_in_readme", readme_url),
                "description": field(description, "curator_transcribed_from_readme", readme_url),
            }
            records.append({"id": f"{server['id']}:{tool_name}", "type": "Tool",
                            "server": server["id"], "fields": tool_fields,
                            "revision": snapshot["revision"]})

    skills_by_repo = {}
    for skill in manifest["agent_skills"]:
        skills_by_repo.setdefault(skill["repository"], []).append(skill)
    for repository, skills in skills_by_repo.items():
        snapshot = snapshots[repository]
        for skill in skills:
            source = source_url(snapshot, skill["skill_md"])
            archive_path = SKILL_ARCHIVE_DIR / f"{repository.replace('/', '__')}__{skill['id']}.zip"
            if archive_path.is_file():
                with zipfile.ZipFile(archive_path) as archive:
                    markdown = archive.read(
                        f"{skill['id']}/{PurePosixPath(skill['skill_md']).name}"
                    ).decode("utf-8", errors="replace")
            else:
                markdown = github_raw(snapshot, skill["skill_md"]).decode("utf-8", errors="replace")
            frontmatter = parse_frontmatter(markdown)
            if not frontmatter.get("name") or not frontmatter.get("description"):
                raise ValueError(f"Skill {skill['id']} is missing name/description frontmatter")
            package_files, archive_path = collect_skill_package(skill, snapshot)
            fields = {
                key: field(frontmatter[key], "explicit_frontmatter", source)
                for key in ("name", "description", "license", "compatibility", "allowed-tools")
                if key in frontmatter
            }
            for absent_key in ("license", "compatibility"):
                if absent_key not in frontmatter:
                    fields[absent_key] = field(None, "not_documented_in_frontmatter", source)
            fields["repository"] = field(
                f"https://github.com/{repository}", "repository_metadata", source
            )
            fields["bundled_files"] = field(
                sorted(str(PurePosixPath(path).relative_to(PurePosixPath(skill["skill_md"]).parent))
                       for path in package_files), "repository_tree_observed", source
            )
            fields["package_archive"] = field(
                str(archive_path.relative_to(ROOT)), "complete_skill_package_downloaded", source
            )
            records.append({"id": skill["id"], "type": "AgentSkill", "server": None,
                            "fields": fields, "revision": snapshot["revision"]})
    return records, snapshots


def persist(records, snapshots):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    collected_at = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript("""
            CREATE TABLE IF NOT EXISTS collection_metadata (
                key TEXT PRIMARY KEY, value TEXT NOT NULL
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
        connection.executemany("INSERT INTO collection_metadata VALUES (?, ?)", [
            ("collected_at", collected_at),
            ("repositories", json.dumps({repository: {
                "branch": snapshot["branch"],
                "revision": snapshot["revision"],
                "files": sorted(snapshot["files"]),
            } for repository, snapshot in snapshots.items()}, sort_keys=True)),
        ])
        for record in records:
            connection.execute("INSERT INTO entity VALUES (?, ?, ?, ?)", (
                record["id"], record["type"], record["server"], record["revision"]
            ))
            for key, item in record["fields"].items():
                connection.execute("INSERT INTO metadata_observation VALUES (?, ?, ?, ?, ?)", (
                    record["id"], key,
                    json.dumps(item["value"], ensure_ascii=False) if item["value"] is not None else None,
                    item["status"], item["source"],
                ))
    with CSV_PATH.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output)
        writer.writerow(["Entity ID", "Entity Type", "Field", "Value", "Evidence Status",
                         "Source", "Revision"])
        for record in records:
            for key, item in record["fields"].items():
                writer.writerow([record["id"], record["type"], key,
                                 json.dumps(item["value"], ensure_ascii=False), item["status"],
                                 item["source"], record["revision"]])


def main():
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    server_count = len(manifest["mcp_servers"])
    skill_count = len(manifest["agent_skills"])
    if server_count < 10 or skill_count < 10:
        raise SystemExit("The curated manifest must contain at least 10 MCP servers and 10 Skills")
    try:
        records, snapshots = collect(manifest)
        persist(records, snapshots)
    except (OSError, urllib.error.URLError, KeyError, ValueError, RuntimeError) as error:
        raise SystemExit(f"Expanded collection failed: {error}") from error

    tool_count = sum(record["type"] == "Tool" for record in records)
    repo_count = len(snapshots)
    print(f"MCP servers: {server_count}; documented tool samples: {tool_count}")
    print(f"Agent Skills: {skill_count}; distinct GitHub repositories: {repo_count}")
    print(f"Database: {DB_PATH}")
    print(f"CSV: {CSV_PATH}")
    print(f"Skill package archives: {SKILL_ARCHIVE_DIR}")
    print(f"MCP README snapshots: {README_DIR}")


if __name__ == "__main__":
    main()
