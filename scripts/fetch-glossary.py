#!/usr/bin/env python3
"""
fetch-glossary.py — Pull glossary terms for each syllabus from curriculum.nsw.edu.au

For each syllabus in data/content/syllabuses.json that has content, fetches the
/glossary page and saves the raw response.

Output:
  data/glossary/{syllabus-slug}.json   ← raw glossary page JSON

Usage:
  python3 scripts/fetch-glossary.py
  python3 scripts/fetch-glossary.py --syllabus chemistry-11-12-2025
  python3 scripts/fetch-glossary.py --force   # re-fetch even if cached
"""

import json
import sys
import time
from pathlib import Path

import requests

BASE_URL = "https://curriculum.nsw.edu.au"
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
CONTENT_DIR = DATA_DIR / "content"
GLOSSARY_DIR = DATA_DIR / "glossary"
STATE_FILE = DATA_DIR / "state.json"
REQUEST_DELAY = 0.5

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})


def get_build_id() -> str:
    import re
    resp = SESSION.get(BASE_URL, timeout=15)
    resp.raise_for_status()
    match = re.search(r"/_next/static/([^/\"]+)/_buildManifest\.js", resp.text)
    if not match:
        raise ValueError("Could not find Next.js build ID")
    return match.group(1)


def fetch_json(url: str) -> dict:
    resp = SESSION.get(url, timeout=30)
    if resp.status_code == 404:
        raise requests.HTTPError("404", response=resp)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    force = "--force" in sys.argv
    target_slug = None
    if "--syllabus" in sys.argv:
        idx = sys.argv.index("--syllabus")
        target_slug = sys.argv[idx + 1]

    # Load syllabuses list
    sylls_path = CONTENT_DIR / "syllabuses.json"
    if not sylls_path.exists():
        print("data/content/syllabuses.json not found — run fetch-content.py first")
        sys.exit(1)
    all_sylls = json.loads(sylls_path.read_text())

    # Only fetch glossaries for syllabuses that have content
    targets = [s for s in all_sylls if (CONTENT_DIR / s["slug"]).exists()]
    if target_slug:
        targets = [s for s in targets if s["slug"] == target_slug]
        if not targets:
            print(f"Not found or no content dir: {target_slug}")
            sys.exit(1)

    GLOSSARY_DIR.mkdir(parents=True, exist_ok=True)

    print("🔍 Getting build ID...")
    build_id = get_build_id()
    print(f"   Build ID: {build_id}")
    print()
    print(f"📖 Fetching glossaries for {len(targets)} syllabus(es)...")

    ok = skip = err = 0
    for syl in targets:
        slug = syl["slug"]
        kla = syl["kla"]
        out_path = GLOSSARY_DIR / f"{slug}.json"

        if out_path.exists() and not force:
            skip += 1
            continue

        url = f"{BASE_URL}/_next/data/{build_id}/learning-areas/{kla}/{slug}/glossary.json"
        time.sleep(REQUEST_DELAY)

        try:
            data = fetch_json(url)
            out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
            items = data.get("pageProps", {}).get("data", {}).get("glossaries", {})
            count = len(items.get("items", [])) if isinstance(items, dict) else 0
            print(f"  ✓ {slug} ({count} terms)")
            ok += 1
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            print(f"  ✗ {slug} ({code})")
            err += 1
        except Exception as exc:
            print(f"  ✗ {slug} ({exc})")
            err += 1

    print()
    print(f"Done: {ok} fetched, {skip} cached, {err} errors")


if __name__ == "__main__":
    main()
