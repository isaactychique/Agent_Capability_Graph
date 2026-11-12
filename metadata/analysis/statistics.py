import csv
import json
from collections import Counter
from pathlib import Path
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
from processing.resolve import groups, key, state

FILES = {"server": "mcp_servers", "skill": "agent_skills", "tool": "mcp_tools"}
INTERNAL = {
    "entity_type",
    "field_states",
    "issues",
    "record_hash",
    "observation_id",
    "raw_file",
    "raw_locator",
    "disposition",
}
REPORT = Path("reports")


def encode(x):
    return json.dumps(
        x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str
    )


def dump(base, rows, columns=None, jsonl=True):
    base = Path(base)
    base.parent.mkdir(parents=True, exist_ok=True)
    columns = columns or sorted(set().union(*(r.keys() for r in rows)))
    with base.with_suffix(".csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, columns)
        w.writeheader()
        for r in rows:
            w.writerow(
                {
                    k: encode(v) if isinstance(v, (list, dict, bool)) else v
                    for k, v in r.items()
                }
            )
    if jsonl:
        base.with_suffix(".jsonl").write_text(
            "".join(encode(r) + "\n" for r in rows), encoding="utf-8"
        )


def chart(name, title, labels, values, xlabel):
    fig, ax = plt.subplots(
        figsize=(8, max(2.8, len(labels) * 0.48 + 1.3)), layout="constrained"
    )
    bars = ax.barh(labels, values, color="#296a72", height=0.62)
    ax.invert_yaxis()
    ax.bar_label(bars, padding=4, fmt="%g")
    ax.set(xlabel=xlabel, title=title, xlim=(0, max([1, *values]) * 1.2))
    ax.spines[["right", "top"]].set_visible(False)
    fig.savefig(REPORT / "figures" / (name + ".png"), dpi=150)
    plt.close(fig)


def table(headers, rows):
    return "\n".join(
        [
            "| " + " | ".join(headers) + " |",
            "|" + "---|" * len(headers),
            *[
                "| "
                + " | ".join(str(v).replace("|", "/").replace("\n", " ") for v in row)
                + " |"
                for row in rows
            ],
        ]
    )


def analyze(obs, canon, events, annotations):
    (REPORT / "figures").mkdir(parents=True, exist_ok=True)
    norm = Path("data/normalized")
    dump(norm / "source_observations", obs)
    dump(
        REPORT / "duplicate_evidence",
        events,
        ["entity_type", "basis", "entity_ids", "observations", "detail"],
    )
    for kind, file in FILES.items():
        dump(norm / file, [r for r in canon if r["entity_type"] == kind])
    dump("data/enriched/capability_annotations", annotations)
    counts = []
    fields = []
    quality = []
    dups = []
    for kind in FILES:
        raw = [r for r in obs if r["entity_type"] == kind]
        entities = [r for r in canon if r["entity_type"] == kind]
        cols = sorted(set().union(*(r.keys() for r in raw)) - INTERNAL)
        for scope, subset in [
            ("canonical", entities),
            *groups(raw, lambda r: r["source_name"]).items(),
        ]:
            if scope != "canonical":
                accepted = [r for r in subset if r["disposition"] == "accepted"]
                counts.append(
                    dict(
                        entity_type=kind,
                        source=scope,
                        raw=len(subset),
                        normalized=len(subset),
                        accepted=len(accepted),
                        quarantined=len(subset) - len(accepted),
                        distinct_accepted_ids=len(set(map(key, accepted))),
                    )
                )
            for k in cols:
                c = Counter(state(r, k) for r in subset)
                fields.append(
                    dict(
                        entity_type=kind,
                        scope=scope,
                        field=k,
                        n=len(subset),
                        **{
                            s: c[s]
                            for s in ["present", "missing", "unknown", "not_applicable"]
                        },
                        missing_rate=c["missing"] / len(subset),
                        availability=c["present"] / len(subset),
                    )
                )
        for issue in sorted(
            {i for r in raw for i in r["issues"]}
            | {
                "invalid_yaml",
                "non_mapping_yaml",
                "missing_name",
                "missing_description",
                "missing_repository",
                "missing_provenance",
                "short_description",
                "unparseable_tool_schema",
                "invalid_url",
                "invalid_type",
                "conflict",
            }
        ):
            quality.append(
                dict(
                    entity_type=kind,
                    issue=issue,
                    n=len(raw),
                    affected=sum(
                        any(
                            x == issue or x.startswith(issue + ":") for x in r["issues"]
                        )
                        for r in raw
                    ),
                )
            )
        basis, field = {
            "server": ("exact_payload", "record_hash"),
            "skill": ("exact_content", "content_hash"),
            "tool": ("repeated_tool_id", "tool_id"),
        }[kind]
        values = [
            r[field] for r in raw if r["disposition"] == "accepted" and r.get(field)
        ]
        excess = len(values) - len(set(values))
        dups.append(
            dict(
                entity_type=kind,
                basis=basis,
                eligible=len(values),
                distinct=len(set(values)),
                excess=excess,
                rate=excess / len(values) if values else None,
            )
        )
    for name, rows in [
        ("source_counts", counts),
        ("field_completeness", fields),
        ("quality_checks", quality),
        ("duplicate_rates", dups),
    ]:
        dump(REPORT / name, rows, jsonl=False)
    chart(
        "source_counts",
        "Source observations by entity type",
        [r["source"] + " · " + r["entity_type"] for r in counts],
        [r["raw"] for r in counts],
        "Observations",
    )
    selected = [
        x
        for x in fields
        if x["scope"] == "canonical"
        and x["field"] in ("name", "description", "source_revision", "repository_url")
    ]
    chart(
        "completeness",
        "Availability in canonical records",
        [x["entity_type"] + " · " + x["field"] for x in selected],
        [round(100 * x["availability"], 1) for x in selected],
        "% of entities of the indicated type",
    )
    selected = [
        x for x in fields if x["scope"] != "canonical" and x["field"] == "description"
    ]
    chart(
        "missing",
        "Missing descriptions in source observations",
        [x["scope"] + " · " + x["entity_type"] for x in selected],
        [round(100 * x["missing_rate"], 1) for x in selected],
        "% of source and type observations",
    )
    chart(
        "duplicates",
        "Excess repeated observations",
        [r["entity_type"] + " · " + r["basis"] for r in dups],
        [r["excess"] for r in dups],
        "Observations beyond the first per matching value",
    )
    actions = Counter(r["capability_action"] for r in annotations)
    chart(
        "capabilities",
        "Candidate action labels on verified tools",
        list(sorted(actions)),
        [actions[k] for k in sorted(actions)],
        "Annotated tools",
    )
    source_quality = []
    for item in counts:
        kind = item["entity_type"]
        common = {"name", "description", "source_url", "source_revision"}
        if kind != "tool":
            common.add("repository_url")
        selected = [
            r
            for r in fields
            if r["entity_type"] == kind
            and r["scope"] == item["source"]
            and r["field"] in common
        ]
        cells = sum(x["n"] for x in selected)
        filled = sum(x["present"] for x in selected)
        source_quality.append(
            dict(
                source=item["source"],
                entity_type=kind,
                fields=sorted(common),
                available_cells=filled,
                total_cells=cells,
                availability=filled / cells,
            )
        )
    dump(REPORT / "source_completeness", source_quality, jsonl=False)
    coverage = []
    for kind in FILES:
        total = sum(r["entity_type"] == kind for r in canon)
        labeled = len(annotations) if kind == "tool" else 0
        coverage.append(
            dict(
                entity_type=kind,
                canonical=total,
                annotated=labeled,
                coverage=labeled / total if total else None,
            )
        )
    dump(REPORT / "annotation_coverage", coverage, jsonl=False)
    dump(
        REPORT / "action_distribution",
        [dict(action=k, tool_count=v) for k, v in sorted(actions.items())],
        jsonl=False,
    )
    return counts, fields, dups


def inventories(obs, canon):
    skill_rows = [r for r in canon if r["entity_type"] == "skill"]
    content = []
    for digest, g in sorted(groups(skill_rows, lambda r: r["content_hash"]).items()):
        content.append(
            dict(
                content_sha256=digest,
                locations=len(g),
                skill_ids=sorted(map(key, g)),
                sources=sorted({r["source_name"] for r in g}),
            )
        )
    dump("data/normalized/skill_contents", content)
    dump(
        "data/normalized/quarantined_skills",
        [r for r in obs if r["disposition"] != "accepted"],
    )
