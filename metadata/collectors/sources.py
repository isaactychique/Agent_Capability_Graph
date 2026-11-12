"""Read-only collection. Cache each completed observation atomically."""

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

RAW = Path("data/raw")
REG = "https://registry.modelcontextprotocol.io"
REPOS = ["anthropics/skills", "microsoft/skills", "vercel-labs/agent-skills"]
FS = "modelcontextprotocol/servers"
HF = "mvaccargiu/gitskills"
session = requests.Session()
session.headers["User-Agent"] = "ACG-semester-metadata/1.0 (public metadata research)"
retry = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
    respect_retry_after_header=True,
)
session.mount("https://", HTTPAdapter(max_retries=retry))


def now():
    return datetime.now(timezone.utc).isoformat()


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".part")
    temp.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )
    temp.replace(path)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def get(url, params=None):
    time.sleep(0.18)
    response = session.get(url, params=params, timeout=(10, 40))
    response.raise_for_status()
    return response


def snapshot(path, url, params=None, project=None):
    path = RAW / path
    if not path.exists():
        r = get(url, params)
        value = project(r) if project else r.json()
        save(path, dict(source_url=r.url, collected_at=now(), data=value))
    return load(path)


def registry(pages=5):
    snapshot("registry_spec.json", REG + "/openapi.json")
    cursor = None
    seen = set()
    for page in range(pages):
        params = {"limit": 100, "version": "latest"}
        if cursor:
            params["cursor"] = cursor
        item = snapshot(f"registry/page-{page:04}.json", REG + "/v0.1/servers", params)
        cursor = item["data"]["metadata"].get("nextCursor")
        if not cursor:
            break
        if cursor in seen:
            raise ValueError("Repeated registry cursor")
        seen.add(cursor)


def pin(repo):
    return snapshot(
        "pins/" + repo + ".json",
        "https://api.github.com/repos/" + repo + "/commits/HEAD",
        project=lambda r: r.json()["sha"],
    )["data"]


def headmatter(data):
    text = data.decode("utf-8-sig")
    m = re.match(r"\A---[ \t]*\r?\n(.*?)^---[ \t]*\r?$", text, re.S | re.M)
    return m.group(1) if m else None


def direct(repo):
    rev = pin(repo)
    tree = snapshot(
        "trees/" + repo + ".json",
        f"https://api.github.com/repos/{repo}/git/trees/{rev}",
        {"recursive": 1},
    )["data"]
    if tree["truncated"]:
        raise ValueError("Incomplete directory inventory: " + repo)
    paths = {x["path"]: x for x in tree["tree"]}
    for path, entry in sorted(paths.items()):
        if entry["mode"] not in ("100644", "100755") or not path.endswith("/SKILL.md"):
            continue
        folder = path.rsplit("/", 1)[0]
        url = f"https://raw.githubusercontent.com/{repo}/{rev}/{quote(path)}"

        def project(r):
            body = r.content
            blob = hashlib.sha1(
                b"blob " + str(len(body)).encode() + b"\0" + body
            ).hexdigest()
            if blob != entry["sha"]:
                raise ValueError("File differs from pinned tree")
            return dict(
                repo=repo,
                path=path,
                revision=rev,
                blob=blob,
                frontmatter=headmatter(body),
                sha256=hashlib.sha256(body).hexdigest(),
                bundles={
                    k: sorted(
                        x[len(folder) + 1 :]
                        for x in paths
                        if x.startswith(folder + "/" + k + "/")
                        and paths[x]["type"] == "blob"
                    )
                    for k in ["scripts", "references", "assets"]
                },
            )

        try:
            snapshot("skills/" + repo + "/" + path + ".json", url, project=project)
        except (ValueError, requests.RequestException) as e:
            failure(url, e)


def filesystem():
    rev = pin(FS)
    for name in ["README.md", "server.ts", "package.json"]:
        snapshot(
            "filesystem/" + name + ".json",
            f"https://raw.githubusercontent.com/{FS}/{rev}/src/filesystem/{name}",
            project=lambda r: r.content.decode("utf-8"),
        )


def secondary(pages=5):
    # Viewer rows do not certify an immutable upstream Git commit.
    for i in [*range(pages), 25000, 50000, 100000, 150000]:

        def project(r):
            result = []
            for entry in r.json()["rows"]:
                row = entry["row"]
                record = {
                    k: row.get(k)
                    for k in (
                        "repo_full_name",
                        "path",
                        "file_sha",
                        "name",
                        "description",
                        "frontmatter_valid",
                        "has_scripts",
                        "has_references",
                        "composition_fetched",
                        "composition_truncated",
                        "discovered_at",
                        "content_sha_ok",
                    )
                }
                body = row.get("content")
                if isinstance(body, str) and "content" not in entry["truncated_cells"]:
                    binary = body.encode()
                    blob = hashlib.sha1(
                        b"blob " + str(len(binary)).encode() + b"\0" + binary
                    ).hexdigest()
                    if blob == row.get("file_sha"):
                        record.update(
                            sha256=hashlib.sha256(binary).hexdigest(),
                            frontmatter=headmatter(binary),
                        )
                record["row_idx"] = entry["row_idx"]
                result.append(record)
            return result

        page = snapshot(
            f"secondary/page-{i:04}.json",
            "https://datasets-server.huggingface.co/rows",
            dict(
                dataset=HF, config="artifacts", split="train", offset=i * 20, length=20
            ),
            project,
        )
        if len(page["data"]) < 20:
            break


def failure(source, error):
    with (RAW / "failures.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(source=source, error=str(error), at=now())) + "\n")
    print(source, str(error), flush=True)


def collect(pages):
    RAW.mkdir(parents=True, exist_ok=True)
    for name, run in [
        ("registry", lambda: registry(pages)),
        *[(r, lambda r=r: direct(r)) for r in REPOS],
        ("filesystem", filesystem),
        ("GitSkills", secondary),
    ]:
        try:
            run()
        except (ValueError, KeyError, requests.RequestException) as e:
            failure(name, e)


def history():
    """A separate unfiltered page to measure version and sample overlap."""
    snapshot("registry/history-first.json", REG + "/v0.1/servers", {"limit": 100})


def linked_registry():
    package = json.loads(load(RAW / "filesystem/package.json.json")["data"])
    name = package.get("mcpName")
    if name:
        snapshot(
            "registry/linked-filesystem.json",
            REG + "/v0.1/servers",
            {"search": name, "version": "latest", "limit": 100},
        )
    rev = pin(FS)
    snapshot(
        "filesystem/LICENSE.json",
        f"https://raw.githubusercontent.com/{FS}/{rev}/LICENSE",
        project=lambda r: r.content.decode("utf-8"),
    )
