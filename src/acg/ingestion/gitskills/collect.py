"""Download the pinned core GitSkills tables, with resumable verified files.

Run from the repository root: python -m src.acg.ingestion.gitskills.collect --cache PATH
The large cache belongs outside the repository. No sibling files are downloaded.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time

import requests

DATASET = "mvaccargiu/gitskills"
REVISION = "ebab17454a7c236f8f26b183567f1a126f42e3f8"
TABLES = ("artifacts", "repos", "mining_runs")


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temp.replace(path)


def manifest(cache):
    target = cache / "manifest.json"
    if target.exists():
        result = json.loads(target.read_text())
        if result["revision"] != REVISION or result["dataset"] != DATASET:
            raise ValueError("Cache belongs to a different dataset revision")
        return result
    files = []
    for table in TABLES:
        url = f"https://huggingface.co/api/datasets/{DATASET}/tree/{REVISION}/data/{table}"
        while url:
            response = requests.get(url, timeout=(15, 90))
            response.raise_for_status()
            for item in response.json():
                if item["type"] == "file" and item["path"].endswith(".parquet"):
                    files.append({"path": item["path"], "size": item["size"],
                                  "sha256": item["lfs"]["oid"]})
            url = response.links.get("next", {}).get("url")
    result = {"dataset": DATASET, "revision": REVISION,
              "created_at": datetime.now(timezone.utc).isoformat(),
              "files": sorted(files, key=lambda x: x["path"])}
    write_json(target, result)
    return result


def download(cache, item):
    path = cache / item["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.stat().st_size == item["size"] and digest(path) == item["sha256"]:
            print(f"Verified cached {item['path']}", flush=True)
            return
        raise ValueError(f"Existing file failed verification: {path}")
    partial = path.with_suffix(".parquet.part")
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/{REVISION}/{item['path']}"
    for attempt in range(5):
        try:
            offset = partial.stat().st_size if partial.exists() else 0
            if offset < item["size"]:
                with requests.get(url, headers={"Range": f"bytes={offset}-"} if offset else {},
                                  stream=True, timeout=(20, 120)) as response:
                    response.raise_for_status()
                    if response.status_code == 206:
                        if not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-"):
                            raise ValueError("Unexpected Content-Range")
                        mode = "ab" if offset else "wb"
                    else:
                        mode = "wb"
                    with partial.open(mode) as stream:
                        for chunk in response.iter_content(4 * 1024 * 1024):
                            stream.write(chunk)
            if partial.stat().st_size != item["size"] or digest(partial) != item["sha256"]:
                raise ValueError(f"Size or SHA-256 mismatch: {partial}")
            partial.replace(path)
            print(f"Downloaded and verified {item['path']} ({item['size']:,} bytes)", flush=True)
            return
        except requests.RequestException:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=3)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    info = manifest(args.cache)
    print(f"Pinned {REVISION}: {len(info['files'])} files, "
          f"{sum(x['size'] for x in info['files']):,} bytes", flush=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(lambda item: download(args.cache, item), info["files"]))
    info["verified_at"] = datetime.now(timezone.utc).isoformat()
    write_json(args.cache / "manifest.json", info)
    print("All core files verified.", flush=True)


if __name__ == "__main__":
    main()
