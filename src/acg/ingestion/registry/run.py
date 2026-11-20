"""Rebuild offline by default. Add --collect to fill the snapshot cache."""

import argparse
import os
from pathlib import Path
from acg.ingestion.registry.collectors.sources import collect, history, failure, linked_registry
from acg.ingestion.registry.processing.normalize import observations
from acg.ingestion.registry.processing.resolve import resolve, annotate
from acg.ingestion.registry.analysis.statistics import analyze, inventories


def main(argv=None):
    from acg.paths import REGISTRY
    os.chdir(REGISTRY)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collect", action="store_true")
    parser.add_argument("--registry-pages", type=int, default=5)
    args = parser.parse_args(argv)
    if args.collect:
        collect(args.registry_pages)
        try:
            history()
            if Path("raw/filesystem/package.json.json").exists():
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
