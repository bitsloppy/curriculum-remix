#!/usr/bin/env python3
"""
fetch-content.py — Pull NSW Curriculum focus-area content pages

For each syllabus found on curriculum.nsw.edu.au:
  1. Discovers the authoritative syllabus list from the live site
  2. Fetches the overview page → gets stage/focus-area entry-point URLs
  3. For each stage: fetches the default FA page → discovers all FAs for that stage
  4. Fetches every focus-area page → saves raw JSON

Output:
  data/content/syllabuses.json            ← source of truth syllabus list
  data/content/{syllabus_slug}/overview.json
  data/content/{syllabus_slug}/{stage_slug}/{fa_id}.json

The syllabuses.json written here is authoritative. Anything in your site data
that isn't in this list was removed from curriculum.nsw.edu.au and should be
removed from your site too.

Usage:
  python3 scripts/fetch-content.py                                   # all syllabuses
  python3 scripts/fetch-content.py --syllabus aboriginal-languages-k-10-2022
  python3 scripts/fetch-content.py --offset 0 --limit 10   # batch 1
  python3 scripts/fetch-content.py --offset 10 --limit 10  # batch 2
  python3 scripts/fetch-content.py --force     # ignore cached build ID check
"""

import json
import re
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_URL = "https://curriculum.nsw.edu.au"
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
CONTENT_DIR = DATA_DIR / "content"
STATE_FILE = DATA_DIR / "state.json"

# Request delay between fetches (seconds) — be polite to Vercel Edge
REQUEST_DELAY = 0.5

# Year-level stage slugs in defaultFocusAreaUrls — these are aliases for the
# stage-level entries and don't have their own distinct content pages.
# We fetch the canonical stage pages; skip these year aliases.
YEAR_SLUG_RE = re.compile(r"^(k|year-[1-9]|year-10)$")


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

SESSION = requests.Session()
SESSION.headers.update({"Accept": "application/json"})


def get_build_id() -> str:
    """Extract the current Next.js build ID from the homepage HTML."""
    resp = SESSION.get(BASE_URL, timeout=15)
    resp.raise_for_status()
    match = re.search(r"/_next/static/([^/\"]+)/_buildManifest\.js", resp.text)
    if not match:
        raise ValueError("Could not find Next.js build ID in homepage HTML")
    return match.group(1)


def fetch_json(url: str, *, retries: int = 2) -> dict:
    """Fetch a Next.js data JSON endpoint. Returns parsed dict."""
    for attempt in range(retries + 1):
        try:
            resp = SESSION.get(url, timeout=30)
            ct = resp.headers.get("content-type", "")
            if resp.status_code == 404:
                raise requests.HTTPError(f"404", response=resp)
            resp.raise_for_status()
            if "application/json" not in ct:
                raise ValueError(f"Expected JSON, got {ct!r} ({len(resp.content)} bytes)")
            return resp.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries:
                raise
            wait = 2 ** attempt
            print(f"      ↻ retry {attempt+1} in {wait}s: {exc}")
            time.sleep(wait)


def next_url(build_id: str, path: str) -> str:
    """Build a /_next/data/ URL from a site path (without leading slash)."""
    return f"{BASE_URL}/_next/data/{build_id}/{path.lstrip('/')}.json"


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Syllabus discovery
# ---------------------------------------------------------------------------

def discover_syllabuses(build_id: str) -> list[dict]:
    """
    Fetch the full syllabus list from the live site.

    curriculum.nsw.edu.au embeds all syllabuses in the pageProps of any
    syllabus overview page. We grab it once from Aboriginal Languages.

    Returns a list of dicts:
      { codename, slug, name, kla, klaLabel, published, doredirect, contentModel }
    """
    seed_url = next_url(
        build_id,
        "learning-areas/languages/aboriginal-languages-k-10-2022/overview",
    )
    print("   Fetching syllabus list from site...")
    data = fetch_json(seed_url)
    items = data["pageProps"]["data"]["syllabuses"]["items"]

    syllabuses = []
    for item in items:
        sys_info = item["system"]
        el = item["elements"]

        codename = sys_info["codename"]
        slug = codename.replace("_", "-")

        kla_vals = el.get("key_learning_area_default", {}).get("value", [])
        kla_code = kla_vals[0]["codename"] if kla_vals else ""
        kla_label = kla_vals[0]["name"] if kla_vals else ""

        doredirect_vals = el.get("doredirect", {}).get("value", [])
        doredirect = bool(doredirect_vals and doredirect_vals[0]["codename"] == "yes")

        content_model_vals = el.get("syllabus_content_model", {}).get("value", [])
        content_model = content_model_vals[0]["codename"] if content_model_vals else "reformed"

        pub_year = el.get("publication_year", {}).get("value", "")

        syllabuses.append(
            {
                "codename": codename,
                "slug": slug,
                "name": sys_info["name"],
                "kla": kla_code,
                "klaLabel": kla_label,
                "contentModel": content_model,
                "publicationYear": pub_year,
                "doredirect": doredirect,
                "lastModified": sys_info.get("lastModified", ""),
            }
        )

    return syllabuses


# ---------------------------------------------------------------------------
# Focus-area discovery and fetching
# ---------------------------------------------------------------------------

def stage_slug_from_path(path: str) -> str:
    """Extract the stage slug from a curriculum.nsw.edu.au path.

    e.g. '/learning-areas/languages/aboriginal-languages-k-10-2022/content/stage-1/fa4140c182'
         → 'stage-1'
    """
    parts = path.rstrip("/").split("/")
    # path looks like: .../content/{stage-slug}/{fa-id}
    # or occasionally:  .../content/{stage-slug}  (no FA yet)
    content_idx = next((i for i, p in enumerate(parts) if p == "content"), None)
    if content_idx is None or content_idx + 1 >= len(parts):
        return ""
    return parts[content_idx + 1]


def fa_id_from_path(path: str) -> str:
    """Extract the focus-area ID from a path."""
    parts = path.rstrip("/").split("/")
    content_idx = next((i for i, p in enumerate(parts) if p == "content"), None)
    if content_idx is None or content_idx + 2 >= len(parts):
        return ""
    return parts[content_idx + 2]


def is_year_slug(stage_slug: str) -> bool:
    """True for year-level URL aliases (k, year-1 … year-10) that duplicate stage pages. NOTE: year-11 and year-12 are real Stage 6 content pages, not aliases."""
    return bool(YEAR_SLUG_RE.match(stage_slug))


def fetch_syllabus_content(build_id: str, syl: dict, *, force: bool = False) -> dict:
    """
    Fetch all focus-area pages for one syllabus.

    Returns summary: { slug, overview_saved, pages_fetched, pages_skipped, errors }
    """
    slug = syl["slug"]
    kla = syl["kla"]
    out_dir = CONTENT_DIR / slug
    summary = {
        "slug": slug,
        "overview_saved": False,
        "pages_fetched": 0,
        "pages_skipped": 0,
        "errors": [],
    }

    # -- Step 1: fetch overview + rationale ------------------------------------
    overview_path = f"learning-areas/{kla}/{slug}/overview"
    overview_url = next_url(build_id, overview_path)
    time.sleep(REQUEST_DELAY)

    try:
        overview_data = fetch_json(overview_url)
    except requests.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            print(f"   ✗ overview 404 — syllabus may not be live yet: {slug}")
            summary["errors"].append("overview_404")
            return summary
        raise

    # Save overview
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "overview.json").write_text(
        json.dumps(overview_data, indent=2, ensure_ascii=False) + "\n"
    )
    summary["overview_saved"] = True

    # Fetch rationale + aim pages
    for page_name in ["rationale", "aim"]:
        page_url = next_url(build_id, f"learning-areas/{kla}/{slug}/{page_name}")
        time.sleep(REQUEST_DELAY)
        try:
            page_data = fetch_json(page_url)
            (out_dir / f"{page_name}.json").write_text(
                json.dumps(page_data, indent=2, ensure_ascii=False) + "\n"
            )
        except Exception:
            pass  # non-fatal

    # -- Step 2: collect entry-point (default) FAs per stage -------------------
    pp_data = overview_data["pageProps"]["data"]
    default_fa_urls: dict = pp_data.get("defaultFocusAreaUrls", {})

    if not default_fa_urls:
        print(f"   ⚠  No defaultFocusAreaUrls found in overview for {slug}")
        return summary

    # Each entry: stage_codename → path like
    #   /learning-areas/{kla}/{slug}/content/{stage-slug}/{fa-id}
    # Deduplicate by (stage_slug, fa_id), skip year-level aliases.
    entry_points: dict[tuple[str, str], str] = {}   # (stage_slug, fa_id) → path
    for _stage_codename, path in default_fa_urls.items():
        s_slug = stage_slug_from_path(path)
        fa_id = fa_id_from_path(path)
        if not s_slug or not fa_id:
            continue
        if is_year_slug(s_slug):
            continue   # year alias — skip
        key = (s_slug, fa_id)
        entry_points[key] = path

    # -- Step 3: fetch each entry-point FA, discover additional FAs -----------
    # We keep a per-stage set of all known FA IDs so we can find extras.
    fetched: set[tuple[str, str]] = set()   # (stage_slug, fa_id)
    pending: list[tuple[str, str]] = list(entry_points.keys())

    while pending:
        s_slug, fa_id = pending.pop(0)

        if (s_slug, fa_id) in fetched:
            summary["pages_skipped"] += 1
            continue

        fa_path = f"learning-areas/{kla}/{slug}/content/{s_slug}/{fa_id}"
        fa_url = next_url(build_id, fa_path)
        time.sleep(REQUEST_DELAY)

        try:
            fa_data = fetch_json(fa_url)
        except requests.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "?"
            print(f"      ✗ {s_slug}/{fa_id} ({code})")
            summary["errors"].append(f"{s_slug}/{fa_id}:{code}")
            fetched.add((s_slug, fa_id))
            continue
        except Exception as exc:
            print(f"      ✗ {s_slug}/{fa_id} ({exc})")
            summary["errors"].append(f"{s_slug}/{fa_id}:err")
            fetched.add((s_slug, fa_id))
            continue

        # Save
        stage_dir = out_dir / s_slug
        stage_dir.mkdir(parents=True, exist_ok=True)
        (stage_dir / f"{fa_id}.json").write_text(
            json.dumps(fa_data, indent=2, ensure_ascii=False) + "\n"
        )
        fetched.add((s_slug, fa_id))
        summary["pages_fetched"] += 1
        print(f"      ✓ {s_slug}/{fa_id}")

        # Discover additional FAs for each stage from stageFocusAreas
        stage_fas = fa_data.get("pageProps", {}).get("data", {}).get("stageFocusAreas", [])
        for sfa_item in stage_fas:
            # FA codename is its URL ID
            sfa_codename = sfa_item.get("system", {}).get("codename", "")
            if not sfa_codename:
                continue
            # Which stages does this FA appear in?
            sfa_stages = sfa_item.get("elements", {}).get("stages__stages", {}).get("value", [])
            for stage_entry in sfa_stages:
                sfa_stage_codename = stage_entry["codename"]   # e.g. "stage_1"
                # Convert to slug: stage_1 → stage-1, early_stage_1 → early-stage-1, life_skills → life-skills
                sfa_stage_slug = sfa_stage_codename.replace("_", "-")
                candidate = (sfa_stage_slug, sfa_codename)
                if candidate not in fetched and candidate not in pending:
                    pending.append(candidate)

    return summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    force = "--force" in sys.argv
    target_slug = None
    batch_offset = None
    batch_limit = None

    if "--syllabus" in sys.argv:
        idx = sys.argv.index("--syllabus")
        if idx + 1 < len(sys.argv):
            target_slug = sys.argv[idx + 1]
    if "--offset" in sys.argv:
        idx = sys.argv.index("--offset")
        batch_offset = int(sys.argv[idx + 1])
    if "--limit" in sys.argv:
        idx = sys.argv.index("--limit")
        batch_limit = int(sys.argv[idx + 1])

    print("🔍 Checking NSW Curriculum for updates...")
    build_id = get_build_id()
    print(f"   Build ID: {build_id}")

    state = load_state()
    is_partial = target_slug is not None or batch_offset is not None or batch_limit is not None
    if build_id == state.get("build_id") and not force and not is_partial:
        print(f"✅ Build unchanged since {state.get('last_fetch', '?')} — nothing to fetch.")
        print("   Use --force to re-fetch, or --syllabus/--offset/--limit for a partial run.")
        return

    # Discover syllabuses
    print()
    syllabuses = discover_syllabuses(build_id)
    non_redirect = [s for s in syllabuses if not s["doredirect"]]
    print(f"   Found {len(syllabuses)} syllabuses, {len(non_redirect)} non-redirect")

    # Save authoritative syllabus list
    CONTENT_DIR.mkdir(parents=True, exist_ok=True)
    (CONTENT_DIR / "syllabuses.json").write_text(
        json.dumps(non_redirect, indent=2, ensure_ascii=False) + "\n"
    )
    print(f"   Saved data/content/syllabuses.json")

    # Filter targets
    if target_slug:
        targets = [s for s in non_redirect if s["slug"] == target_slug]
        if not targets:
            print(f"\n❌ Syllabus not found: {target_slug}")
            print(f"   Known slugs: {[s['slug'] for s in non_redirect[:5]]} ...")
            sys.exit(1)
    elif batch_offset is not None or batch_limit is not None:
        offset = batch_offset or 0
        limit = batch_limit or len(non_redirect)
        targets = non_redirect[offset : offset + limit]
        print(f"   Batch: syllabuses {offset + 1}–{offset + len(targets)} of {len(non_redirect)}")
    else:
        targets = non_redirect

    print(f"\n📥 Fetching content for {len(targets)} syllabus(es)...\n")

    all_errors = []
    total_pages = 0

    for i, syl in enumerate(targets, 1):
        prefix = f"[{i}/{len(targets)}]"
        print(f"{prefix} {syl['name']} ({syl['kla']})")
        try:
            result = fetch_syllabus_content(build_id, syl, force=force)
        except Exception as exc:
            print(f"   ❌ Unexpected error: {exc}")
            all_errors.append(syl["slug"])
            continue

        total_pages += result["pages_fetched"]
        if result["errors"]:
            all_errors.append(syl["slug"])
            print(f"   ⚠  {result['pages_fetched']} pages, {len(result['errors'])} error(s)")
        else:
            print(f"   ✓ {result['pages_fetched']} pages saved")
        print()

    # Update state (only if we fetched everything, not a partial run)
    if not target_slug and batch_offset is None and batch_limit is None:
        state["build_id"] = build_id
        from datetime import datetime
        state["last_fetch"] = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        state["content_syllabuses"] = len(non_redirect)
        state["content_pages"] = total_pages
        save_state(state)

        # Update site meta.json with today's fetch date
        meta_file = REPO_ROOT / "site" / "src" / "data" / "meta.json"
        meta = {"dataFetchedAt": datetime.now().strftime("%Y-%m-%d")}
        meta_file.write_text(json.dumps(meta, indent=2) + "\n")
        print(f"   Updated site/src/data/meta.json → {meta['dataFetchedAt']}")

    print(f"{'✅' if not all_errors else '⚠️ '} Done — {total_pages} pages total")
    if all_errors:
        print(f"   Errors in: {all_errors}")
        sys.exit(1)


if __name__ == "__main__":
    main()
