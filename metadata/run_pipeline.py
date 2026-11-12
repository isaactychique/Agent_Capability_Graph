"""Rebuild offline by default. Add --collect to fill the snapshot cache."""

import argparse
import os
from pathlib import Path
from collectors.sources import collect, history, failure, linked_registry
from processing.normalize import observations
from processing.resolve import resolve, annotate
from analysis.statistics import analyze, inventories


def main():
    os.chdir(Path(__file__).resolve().parent)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--registry-pages", type=int, default=5)
    args = parser.parse_args()
    if args.collect:
        collect(args.registry_pages)
        try:
            history()
            if Path("data/raw/filesystem/package.json.json").exists():
                linked_registry()
        except Exception as error:
            failure("registry supplement / filesystem license", error)
    obs = observations()
    if not obs:
        parser.error("No cached observations. Run with --collect.")
    canon, events = resolve(obs)
    annotations = annotate(canon)
    analyze(obs, canon, events, annotations)
    inventories(obs, canon)
    print(
        f"{len(obs)} observations, {len(canon)} canonical entities, {len(annotations)} annotations"
    )


if __name__ == "__main__":
    main()
