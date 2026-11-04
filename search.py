#!/usr/bin/env python3
"""Tiny keyword-search prototype over data/examples.json."""

import argparse
import json
import re
from pathlib import Path


DATA_FILE = Path(__file__).resolve().parent / "data" / "examples.json"


def normalize(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def contains_all_terms(text, terms):
    words = set(normalize(text).split())
    return all(term in words for term in terms)


def main():
    parser = argparse.ArgumentParser(
        description="Search the project's example MCP servers and Agent Skills."
    )
    parser.add_argument("query", nargs="+", help="Capability words to search for")
    parser.add_argument(
        "--type",
        choices=("all", "mcp_server", "agent_skill"),
        default="all",
        help="Limit results to one kind of capability record",
    )
    args = parser.parse_args()
    query = " ".join(args.query)
    terms = normalize(query).split()

    try:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        parser.error(f"Cannot read {DATA_FILE}: {error}")

    results = []
    for record in data.get("examples", []):
        if args.type != "all" and record.get("type") != args.type:
            continue

        summary = " ".join(
            str(record.get(field, ""))
            for field in ("name", "description", "instructions_summary")
        )
        summary += " " + " ".join(record.get("dependencies_mentioned", []))
        matched_tools = [
            tool
            for tool in record.get("tools", [])
            if contains_all_terms(
                " ".join(str(value) for value in tool.values()), terms
            )
        ]

        if contains_all_terms(summary, terms) or matched_tools:
            results.append((record, matched_tools))

    if not results:
        print(f'No matches for "{query}".')
        return

    print(f'{len(results)} match(es) for "{query}":')
    for record, matched_tools in results:
        print(
            f"\n- {record.get('name', 'Unnamed')} "
            f"[{record.get('type', 'unknown')}] ({record.get('id', 'no id')})"
        )
        if matched_tools:
            print("  Matching tools:")
            for tool in matched_tools:
                print(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', '')}")
        else:
            print("  Match found in the record description or instructions.")

    print("\nPrototype note: this is keyword matching, not semantic or RDF graph search.")


if __name__ == "__main__":
    main()
