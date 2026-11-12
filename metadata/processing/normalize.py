"""Map evidence to typed observations; retain null and its reason separately."""

import hashlib
import json
import re
from urllib.parse import quote, urlsplit
import yaml
from collectors.sources import RAW, REG, FS, load


def ident(kind, *parts):
    return (
        kind
        + "_"
        + hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()[
            :24
        ]
    )


def clean(value):
    return value.strip() or None if isinstance(value, str) else None


def valid_url(value):
    try:
        u = urlsplit(value)
        return (
            u.scheme in ("https", "http")
            and bool(u.hostname)
            and not re.search(r"\s", value)
        )
    except (TypeError, ValueError):
        return False


class UniqueKeys(yaml.SafeLoader):
    """Reject duplicate YAML keys instead of silently taking the last one."""

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        pairs = self.construct_pairs(node, deep=deep)
        try:
            result = dict(pairs)
        except TypeError as exc:
            raise yaml.YAMLError("unhashable mapping key") from exc
        if len(result) != len(pairs):
            raise yaml.YAMLError("duplicate mapping key")
        return result


def headers(text):
    if text is None:
        return {}, "no_frontmatter"
    try:
        data = yaml.load(text, Loader=UniqueKeys)
        if isinstance(data, dict):
            return data, None
        return {}, "non_mapping_yaml"
    except yaml.YAMLError:
        return {}, "invalid_yaml"


def base(kind, path, snap, source, idx):
    return dict(
        entity_type=kind,
        observation_id=ident("obs", str(path), idx),
        raw_file=str(path),
        raw_locator=str(idx),
        source_name=source,
        source_url=snap["source_url"],
        collected_at=snap["collected_at"],
        source_revision=None,
        issues=[],
        field_states={},
    )


def repo_url(data, row):
    aliases = ["repository", "repository_url", "repo", "github_url", "sourceCodeUrl"]
    candidates = []
    for alias in aliases:
        value = data.get(alias)
        if isinstance(value, dict):
            value = value.get("url")
        if clean(value):
            candidates.append(clean(value))
        elif value is not None and not isinstance(value, str):
            row["issues"].append("invalid_type:repository_url")
    if len(set(candidates)) > 1:
        row["issues"].append("conflict:repository_url")
    return candidates[0] if candidates else None


def server_rows():
    for p in sorted((RAW / "registry").glob("*.json")):
        snap = load(p)
        for i, item in enumerate(snap["data"]["servers"]):
            s = item["server"]
            r = base("server", p, snap, "Official MCP Registry", i)
            name = clean(s.get("name"))
            pk = s.get("packages") or []
            rem = s.get("remotes") or []
            meta = item.get("_meta", {}).get(
                "io.modelcontextprotocol.registry/official", {}
            )
            packages = [
                {"registry": x.get("registryType"), "identifier": x.get("identifier")}
                for x in pk
            ]
            r.update(
                server_id=ident("srv", "registry", name or r["observation_id"]),
                name=name,
                description=clean(s.get("description")),
                version=clean(s.get("version")),
                repository_url=repo_url(s, r),
                source_revision=None,
                registry_url=REG
                + "/v0.1/servers/"
                + quote(name, safe="")
                + "/versions/"
                + quote(s["version"], safe="")
                if name and s.get("version")
                else None,
                package_identifier=packages or None,
                transport=sorted(
                    {
                        t
                        for t in [
                            *(x.get("type") for x in rem),
                            *((x.get("transport") or {}).get("type") for x in pk),
                        ]
                        if t
                    }
                )
                or None,
                license=clean(s.get("license") or s.get("licence")),
                is_latest=meta.get("isLatest"),
                published_at=meta.get("publishedAt"),
                updated_at=meta.get("updatedAt"),
                record_hash=hashlib.sha256(
                    json.dumps(item, sort_keys=True).encode()
                ).hexdigest(),
            )
            if not pk and rem:
                r["field_states"]["package_identifier"] = "not_applicable"
            yield r


def skill_row(p, snap, d, secondary=False):
    repo = d["repo_full_name" if secondary else "repo"]
    path = d["path"]
    src = "GitSkills (secondary)" if secondary else repo
    r = base("skill", p, snap, src, d["row_idx"] if secondary else path)
    meta, err = headers(d.get("frontmatter"))
    if err:
        if secondary and "frontmatter" not in d:
            err = (
                "upstream_invalid_frontmatter"
                if d["frontmatter_valid"] == 0
                else "frontmatter_unverified"
            )
        r["issues"].append(err)
    extra = meta.get("metadata")
    if extra is not None and not isinstance(extra, dict):
        r["issues"].append("invalid_type:metadata")

    def field(k, *aliases):
        values = [meta[a] for a in (k, *aliases) if a in meta and meta[a] is not None]
        if not values:
            return None
        if any(v != values[0] for v in values[1:]):
            r["issues"].append("conflict:" + k)
        if not isinstance(values[0], str):
            r["issues"].append("invalid_type:" + k)
            r["field_states"][k] = "unknown"
        return clean(values[0])

    name = field("name")
    desc = field("description")
    if secondary:
        for k, parsed in [("name", name), ("description", desc)]:
            if parsed and clean(d.get(k)) and parsed != clean(d[k]):
                r["issues"].append("upstream_conflict:" + k)
        name = name or clean(d.get("name"))
        desc = desc or clean(d.get("description"))
    allowed = meta.get("allowed-tools", meta.get("allowed_tools"))
    if isinstance(allowed, str):
        allowed = re.findall(r"(?:[^\s,()]+\([^)]*\)|[^\s,]+)", allowed)
    if allowed is not None and not (
        isinstance(allowed, list) and all(isinstance(v, str) for v in allowed)
    ):
        allowed = None
        r["issues"].append("invalid_type:allowed_tools")
        r["field_states"]["allowed_tools"] = "unknown"
    deps = meta.get(
        "dependencies",
        (extra or {}).get("dependencies") if isinstance(extra, dict) else None,
    )
    if deps is not None and not isinstance(deps, (list, str, dict)):
        deps = None
        r["issues"].append("invalid_type:dependencies")
        r["field_states"]["dependencies"] = "unknown"
    r.update(
        skill_id=ident("skl", repo.casefold(), path),
        name=name,
        description=desc,
        repository_url="https://github.com/" + repo,
        skill_path=path,
        license=field("license", "licence"),
        compatibility=field("compatibility"),
        allowed_tools=allowed,
        dependencies=deps,
        dependency_basis="declared" if deps is not None else None,
        content_hash=d.get("sha256"),
        source_revision=d.get("revision"),
        blob_sha=d.get("blob", d.get("file_sha")),
        source_kind="secondary_import" if secondary else "direct_file",
    )
    r["upstream_blob_url"] = (
        ("https://api.github.com/repos/" + repo + "/git/blobs/" + r["blob_sha"])
        if r["blob_sha"]
        else None
    )
    for k in ("scripts", "references", "assets"):
        v = None
        if not secondary:
            v = bool(d["bundles"][k])
        elif d.get("composition_fetched") and d.get("has_" + k) is not None:
            if d["has_" + k] or not d.get("composition_truncated"):
                v = bool(d["has_" + k])
        r["has_" + k] = v
    if secondary:
        for k in [
            "source_revision",
            "content_hash",
            "has_assets",
            "has_scripts",
            "has_references",
        ]:
            if r[k] is None:
                r["field_states"][k] = "unknown"
        if err:
            for k in ["license", "compatibility", "allowed_tools", "dependencies"]:
                if r[k] is None:
                    r["field_states"][k] = "unknown"
    return r


def skill_rows():
    for p in sorted((RAW / "skills").rglob("*.json")):
        s = load(p)
        yield skill_row(p, s, s["data"])
    for p in sorted((RAW / "secondary").glob("*.json")):
        s = load(p)
        for d in s["data"]:
            yield skill_row(p, s, d, True)


def filesystem_rows():
    p = RAW / "filesystem/package.json.json"
    if not p.exists():
        return
    s = load(p)
    pkg = json.loads(s["data"])
    rev = load(RAW / "pins" / (FS + ".json"))["data"]
    sid = ident("srv", "npm", pkg["name"])
    r = base("server", p, s, FS, "package.json")
    r.update(
        server_id=sid,
        name=pkg["name"],
        version=pkg["version"],
        description=pkg.get("description"),
        package_identifier=[dict(registry="npm", identifier=pkg["name"])],
        repository_url="https://github.com/" + FS,
        source_revision=rev,
        license=pkg.get("license"),
        registry_url=None,
        transport=None,
        is_latest=None,
        published_at=None,
        updated_at=None,
        record_hash=hashlib.sha256(s["data"].encode()).hexdigest(),
    )
    r["field_states"].update(registry_url="not_applicable", is_latest="not_applicable")
    yield r
    p = RAW / "filesystem/server.ts.json"
    if not p.exists():
        return
    snap = load(p)
    code = snap["data"]
    shapes = dict(
        re.findall(r"const (\w+) = z\.object\(\{\n(.*?)^\}\);", code, re.S | re.M)
    )
    for m in re.finditer(
        r'server\.registerTool\(\s*"([^"]+)",\s*\{(.*?)\n    \},', code, re.S
    ):
        name, config = m.groups()
        r = base("tool", p, snap, FS, name)
        line = code.count("\n", 0, m.start()) + 1
        r.update(
            tool_id=ident("tool", sid, name),
            server_id=sid,
            name=name,
            source_revision=rev,
            source_url=f"https://github.com/{FS}/blob/{rev}/src/filesystem/server.ts#L{line}",
            evidence_type="static_registration",
            schema_format="TypeScript/Zod",
            input_schema=None,
            output_schema=None,
            required_parameters=None,
            read_only_hint=None,
            description=None,
        )
        desc = re.search(r"\bdescription:\s*(.*?),\s*inputSchema:", config, re.S)
        if desc:
            strings = re.findall(r'"(?:\\.|[^"\\])*"', desc[1])
            r["description"] = "".join(json.loads(x) for x in strings) or None
        inp = re.search(r"inputSchema: jsonSchema2020\((\w+)\.shape\)", config)
        out = re.search(r"outputSchema: (.*?),\n      annotations:", config, re.S)
        hint = re.search(r"readOnlyHint: (true|false)", config)
        if hint:
            r["read_only_hint"] = hint[1] == "true"
        if inp and inp[1] in shapes:
            shape = shapes[inp[1]]
            r["input_schema"] = "z.object({\n" + shape + "})"
            fields = re.findall(r"^  (\w+): (.*?)(?=^  \w+: |\Z)", shape, re.S | re.M)
            r["required_parameters"] = [
                k for k, v in fields if ".optional()" not in v and ".default(" not in v
            ]
        elif "inputSchema: jsonSchema2020({})" in config:
            r.update(input_schema="jsonSchema2020({})", required_parameters=[])
        if out:
            r["output_schema"] = out[1]
        if not (r["input_schema"] and r["output_schema"]):
            r["issues"].append("unparseable_tool_schema")
        yield r


def observations():
    rows = [*server_rows(), *skill_rows(), *filesystem_rows()]
    for r in rows:
        for k in ("name", "description"):
            if not r.get(k):
                r["issues"].append("missing_" + k)
        if r.get("description") and len(r["description"]) < 30:
            r["issues"].append("short_description")
        for k in ("source_url", "registry_url", "repository_url"):
            if r.get(k) and not valid_url(r[k]):
                r["issues"].append("invalid_url:" + k)
                r[k] = None
                r["field_states"][k] = "unknown"
        if "repository_url" in r and not r["repository_url"]:
            r["issues"].append("missing_repository")
        if not r["source_url"] or not r["collected_at"]:
            r["issues"].append("missing_provenance")
    return rows
