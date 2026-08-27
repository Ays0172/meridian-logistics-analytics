"""
build_manifest.py - writes 02_data/_state/manifest.json listing every
live-feed parquet file (date-stamped, e.g. part-20260826-00.parquet)
as a direct raw.githubusercontent.com URL, grouped by table.

Deliberately excludes frozen-history files (part-000.parquet) - those
are never committed to git (see .gitignore) and are not reachable by
URL; they are distributed via the GitHub Release asset instead and
should be loaded once, locally, in Power BI.

Run from 01_generator/, same as live_feed.py.
"""
import json
import re
import os
from pathlib import Path

REPO = "Ays0172/meridian-logistics-analytics"
BRANCH = "main"
RAW_ROOT = Path("../02_data/raw")
OUT_PATH = Path("../02_data/_state/manifest.json")

LIVE_FILE_RE = re.compile(r"^part-\d{8}-\d{2}\.parquet$")

def raw_url(rel_path: str) -> str:
    rel_path = rel_path.replace(os.sep, "/")
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/02_data/raw/{rel_path}"

def main():
    tables = {}
    for table_dir in sorted(p for p in RAW_ROOT.iterdir() if p.is_dir()):
        table = table_dir.name
        urls = []
        for f in sorted(table_dir.rglob("*.parquet")):
            if LIVE_FILE_RE.match(f.name):
                rel = f.relative_to(RAW_ROOT)
                urls.append(raw_url(str(rel)))
        if urls:
            tables[table] = urls

    manifest = {
        "repo": REPO,
        "branch": BRANCH,
        "note": "Live-feed files only. Frozen history ships separately as a GitHub Release asset (history-v1) and should be loaded once, locally.",
        "tables": tables,
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(manifest, indent=2))

    total = sum(len(v) for v in tables.values())
    print(f"manifest.json written: {len(tables)} tables, {total} live-feed files")

if __name__ == "__main__":
    main()