"""Separate source versions, distributions and byte-identical content."""

from collections import defaultdict
import json
import re
from processing.normalize import ident


def key(r):
    return r[r["entity_type"] + "_id"]


def groups(rows, fn):
    g = defaultdict(list)
    for r in rows:
        value = fn(r)
        if value is not None:
            g[value].append(r)
    return g


def state(r, k):
    if k in r["field_states"]:
        return r["field_states"][k]
    return "present" if r.get(k) is not None else "missing"


def resolve(rows):
    canon = []
    events = []
    eligible = []
    for r in rows:
        r["disposition"] = "accepted"
        if r["entity_type"] == "skill" and not (r["name"] and r["description"]):
            r["disposition"] = "quarantined_incomplete_frontmatter"
        else:
            eligible.append(r)

    def event(kind, basis, group, detail):
        events.append(
            dict(
                entity_type=kind,
                basis=basis,
                entity_ids=sorted(set(map(key, group))),
                observations=[x["observation_id"] for x in group],
                detail=detail,
            )
        )

    for entity, group in sorted(groups(eligible, key).items()):
        best = max(
            group,
            key=lambda r: (
                r.get("is_latest") is True,
                r.get("source_kind") == "direct_file",
                r.get("updated_at") or "",
                r["collected_at"],
                r["observation_id"],
            ),
        )
        canon.append(best.copy())
        for version, subset in groups(group, lambda r: r.get("version", "")).items():
            for k in [
                "description",
                "license",
                "repository_url",
                "content_hash",
                "package_identifier",
            ]:
                vals = {
                    json.dumps(r[k], sort_keys=True, ensure_ascii=False)
                    for r in subset
                    if r.get(k) is not None
                }
                if len(vals) > 1:
                    event(best["entity_type"], "conflicting_" + k, subset, sorted(vals))
        if len(group) > 1:
            event(
                best["entity_type"],
                "same_identity",
                group,
                sorted({r.get("version") or "" for r in group}),
            )
    for kind in ("skill", "server", "tool"):
        subset = [r for r in canon if r["entity_type"] == kind]
        for name, group in groups(
            subset, lambda r: (r.get("name") or "").casefold().rsplit("/", 1)[-1]
        ).items():
            if name and len(group) > 1:
                event(kind, "name_candidate", group, name)
    for digest, group in groups(
        [r for r in eligible if r["entity_type"] == "skill"],
        lambda r: r.get("content_hash"),
    ).items():
        if len(group) > 1:
            event("skill", "exact_content", group, digest)
    for digest, group in groups(
        [r for r in eligible if r["entity_type"] == "server"],
        lambda r: r.get("record_hash"),
    ).items():
        if len(group) > 1:
            event("server", "exact_payload", group, digest)
    packages = defaultdict(list)
    for r in canon:
        for p in r.get("package_identifier") or []:
            if p["identifier"]:
                packages[(p["registry"], p["identifier"])].append(r)
    for pkg, group in packages.items():
        if len(set(map(key, group))) > 1:
            event("server", "shared_package_candidate", group, list(pkg))
    for repo, group in groups(
        [x for x in canon if x["entity_type"] == "server"],
        lambda r: (
            r.get("repository_url", "")
            and re.sub(r"\.git$", "", r["repository_url"].rstrip("/"))
        ),
    ).items():
        if len(group) > 1:
            event("server", "shared_repository_candidate", group, repo)
    return canon, events


# Deliberately small vocabulary. Each mapping is tied to a verified static registration.
ACTIONS = {
    "read_file": ("read", "file"),
    "read_text_file": ("read", "file"),
    "read_media_file": ("read", "file"),
    "read_multiple_files": ("read", "file"),
    "write_file": ("write", "file"),
    "append_file": ("write", "file"),
    "edit_file": ("write", "file"),
    "create_directory": ("create", "directory"),
    "list_directory": ("list", "directory"),
    "list_directory_with_sizes": ("list", "directory"),
    "directory_tree": ("list", "directory"),
    "move_file": ("move", "filesystem entry"),
    "copy_file": ("copy", "file"),
    "search_files": ("search", "filesystem entry"),
    "get_file_info": ("read", "filesystem entry"),
    "list_allowed_directories": ("list", "directory"),
}


def annotate(rows):
    result = []
    for r in rows:
        if r["entity_type"] != "tool" or r["name"] not in ACTIONS:
            continue
        action, obj = ACTIONS[r["name"]]
        result.append(
            dict(
                annotation_id=ident("ann", key(r), "v1"),
                tool_id=key(r),
                name=r["name"],
                capability_action=action,
                capability_object=obj,
                state_change=action in {"write", "move", "create", "copy"},
                requires_authentication="unknown",
                evidence_type="inferred_from_static_registration",
                evidence_source=r["source_url"],
                evidence_text=r["description"],
                declared_read_only_hint=r["read_only_hint"],
                review_status="candidate_for_human_review",
            )
        )
    return result
