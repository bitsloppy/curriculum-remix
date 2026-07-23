#!/usr/bin/env python3
"""
fetch-data.py — Pull NSW Curriculum data from curriculum.nsw.edu.au

How it works:
  1. Fetches the site homepage to extract the current Next.js build ID
  2. Compares to the last known build ID (stored in data/state.json)
  3. If the build changed (or --force is passed), fetches all page JSON
  4. Saves each page as a JSON file in data/snapshots/<timestamp>_<build-id>/
  5. Updates data/state.json with the new build info

Usage:
  python3 scripts/fetch-data.py           # only fetches if build ID changed
  python3 scripts/fetch-data.py --force   # always fetch, even if same build
"""

import requests
import json
import re
import sys
from datetime import datetime
from pathlib import Path

BASE_URL = "https://curriculum.nsw.edu.au"
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
STATE_FILE = DATA_DIR / "state.json"

# Pages to fetch: URL slug → output filename
# The Next.js data endpoint is: BASE_URL/_next/data/<build_id>/<slug>.json
PAGES = {
    "learning-areas":               "learning-areas.json",
    "learning-areas/english":       "english.json",
    "learning-areas/mathematics":   "mathematics.json",
    "learning-areas/science":       "science.json",
    "learning-areas/tas":            "technologies.json",
    "learning-areas/hsie":          "hsie.json",
    "learning-areas/creative-arts": "creative-arts.json",
    "learning-areas/pdhpe":         "pdhpe.json",
    "learning-areas/languages":     "languages.json",
    "learning-areas/vet":           "vet.json",
}


def get_build_id() -> str:
    """Extract the Next.js build ID from the homepage HTML.

    The build ID appears in JS bundle paths:
      /_next/static/<build_id>/_buildManifest.js
    """
    resp = requests.get(BASE_URL, timeout=15)
    resp.raise_for_status()
    match = re.search(r'/_next/static/([^/"]+)/_buildManifest\.js', resp.text)
    if not match:
        raise ValueError("Could not find Next.js build ID in homepage HTML")
    return match.group(1)


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def fetch_page(build_id: str, slug: str) -> dict:
    """Fetch a page's pre-rendered Next.js data JSON."""
    url = f"{BASE_URL}/_next/data/{build_id}/{slug}.json"
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    force = "--force" in sys.argv

    print("🔍 Checking NSW Curriculum for updates...")
    try:
        build_id = get_build_id()
    except Exception as e:
        print(f"❌ Failed to get build ID: {e}")
        sys.exit(1)

    print(f"   Build ID: {build_id}")

    state = load_state()
    last_build_id = state.get("build_id")

    if build_id == last_build_id and not force:
        print(f"✅ Already up to date (build {build_id})")
        print(f"   Last fetched: {state.get('last_fetch', 'unknown')}")
        print("   Use --force to re-fetch anyway.")
        return

    if last_build_id and last_build_id != build_id:
        print(f"   Previous build: {last_build_id} → new build detected!")
    elif force:
        print("   --force flag set, re-fetching...")

    # Create snapshot directory named by timestamp + build ID
    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    snapshot_name = f"{timestamp}_{build_id}"
    snapshot_dir = SNAPSHOTS_DIR / snapshot_name
    snapshot_dir.mkdir(parents=True, exist_ok=True)

    # Fetch all pages
    print(f"\n📥 Fetching {len(PAGES)} pages into snapshots/{snapshot_name}/\n")
    errors = []
    for slug, filename in PAGES.items():
        try:
            data = fetch_page(build_id, slug)
            (snapshot_dir / filename).write_text(
                json.dumps(data, indent=2, ensure_ascii=False) + "\n"
            )
            print(f"   ✓  {slug}")
        except requests.HTTPError as e:
            print(f"   ✗  {slug}  ({e.response.status_code})")
            errors.append(slug)
        except Exception as e:
            print(f"   ✗  {slug}  ({e})")
            errors.append(slug)

    # Save state
    state["build_id"] = build_id
    state["last_fetch"] = timestamp
    state["snapshot"] = snapshot_name
    if errors:
        state["last_errors"] = errors
    else:
        state.pop("last_errors", None)
    save_state(state)

    # Summary
    fetched = len(PAGES) - len(errors)
    print(f"\n{'✅' if not errors else '⚠️ '} Done — {fetched}/{len(PAGES)} pages fetched")
    print(f"   Snapshot: data/snapshots/{snapshot_name}/")
    if errors:
        print(f"   Failed:   {', '.join(errors)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
