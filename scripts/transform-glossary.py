#!/usr/bin/env python3
"""
transform-glossary.py — Convert raw glossary JSON → site-ready data files

Reads:  data/glossary/{slug}.json
Writes:
  site/src/data/glossary/{slug}.json     ← per-syllabus: { shared[], specific[] }
  site/src/data/glossary-map.json        ← { id: { title, slug, description } }

Each term object:
  { id, codename, title, slug, description }

shared   = terms with empty syllabus[] (apply to all syllabuses)
specific = terms tagged to this syllabus only

Usage:
  python3 scripts/transform-glossary.py
  python3 scripts/transform-glossary.py --syllabus chemistry-11-12-2025
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
GLOSSARY_SRC = REPO_ROOT / "data" / "glossary"
GLOSSARY_OUT = REPO_ROOT / "site" / "src" / "data" / "glossary"
MAP_OUT = REPO_ROOT / "site" / "src" / "data" / "glossary-map.json"

EMPTY_HTML = {"<p><br></p>", "<p></p>", ""}


def clean_html(html: str) -> str:
    """Strip empty Kentico placeholders."""
    if not html or html in EMPTY_HTML:
        return ""
    return re.sub(
        r'<object[^>]+type="application/kenticocloud"[^>]*/?>(?:</object>)?',
        "",
        html,
    ).strip()


def parse_term(item: dict) -> dict | None:
    sys_info = item.get("system", {})
    el = item.get("elements", {})

    term_id = sys_info.get("id", "")
    codename = sys_info.get("codename", "")
    title = el.get("title", {}).get("value", "").strip()
    slug = el.get("slug", {}).get("value", "").strip()
    desc_raw = el.get("description", {}).get("value", "")
    description = clean_html(desc_raw)
    syllabuses = [s.get("codename", "") for s in el.get("syllabus", {}).get("value", [])]

    if not title:
        return None

    return {
        "id": term_id,
        "codename": codename,
        "title": title,
        "slug": slug,
        "description": description,
        "syllabuses": syllabuses,
    }


def transform_syllabus(slug: str, all_map: dict) -> dict | None:
    src = GLOSSARY_SRC / f"{slug}.json"
    if not src.exists():
        return None

    raw = json.loads(src.read_text())
    glossaries = raw.get("pageProps", {}).get("data", {}).get("glossaries")
    if not glossaries or not isinstance(glossaries, dict):
        return None

    items = glossaries.get("items", []) or []

    shared = []
    specific = []

    for item in items:
        term = parse_term(item)
        if not term:
            continue

        # Add to global map (id → lightweight record for popover lookup)
        all_map[term["id"]] = {
            "title": term["title"],
            "slug": term["slug"],
            "description": term["description"],
        }

        # Categorise
        entry = {k: term[k] for k in ("id", "codename", "title", "slug", "description")}
        if not term["syllabuses"]:
            shared.append(entry)
        else:
            specific.append(entry)

    # Sort both alphabetically
    shared.sort(key=lambda t: t["title"].lower())
    specific.sort(key=lambda t: t["title"].lower())

    return {"shared": shared, "specific": specific}




# ─────────────────────────────────────────────────────────────────────────────
# Link-ID map: scan FA raw files to resolve data-item-id → glossary term
# ─────────────────────────────────────────────────────────────────────────────

def derive_slug_candidates(codename: str) -> list[str]:
    """
    Derive glossary slug candidates from a glo_link__* codename.
    e.g. 'glo_link__shared__scientific_investigation' -> ['scientific-investigation']
         'glo_link__mst__independent_variable__science_' -> ['independent-variable', 'independent-variable-science']
    """
    # Strip known prefixes (glo_link__<kla>__ or glo_link__shared__ or glo_link__)
    s = re.sub(r'^glo_link__(?:[a-z0-9]+__)?', '', codename)
    if not s:
        return []
    # Split on double underscore (qualifier suffixes like __science_, __networks_)
    parts = re.split(r'_{2,}', s)
    base = parts[0].replace('_', '-').strip('-')
    full = s.replace('__', '-').replace('_', '-').strip('-')
    candidates = []
    if base:
        candidates.append(base)
    if full and full != base:
        candidates.append(full)
    return candidates


def build_link_id_map(
    content_dir: Path,
    slug_map: dict[str, dict],
) -> dict[str, dict]:
    """
    Scan raw FA JSON files to find all link_glossary links.
    Returns {linkId: {title, slug, description}}.
    """
    link_id_map: dict[str, dict] = {}

    for fa_path in content_dir.rglob("*.json"):
        if fa_path.name in ("syllabuses.json", "overview.json", "rationale.json", "aim.json"):
            continue
        try:
            raw = json.loads(fa_path.read_text())
        except Exception:
            continue

        li = (
            raw.get("pageProps", {})
            .get("data", {})
            .get("focusArea", {})
            .get("linkedItems", {})
        )
        for item in li.values():
            el = item.get("elements", {})
            for field in el.values():
                if not isinstance(field, dict):
                    continue
                links = field.get("links")
                if not isinstance(links, list):
                    continue
                for link in links:
                    if link.get("type") != "link_glossary":
                        continue
                    link_id = link.get("linkId", "")
                    codename = link.get("codename", "")
                    if not link_id or link_id in link_id_map:
                        continue
                    for slug in derive_slug_candidates(codename):
                        term = slug_map.get(slug)
                        if term:
                            link_id_map[link_id] = {
                                "title": term["title"],
                                "slug": slug,
                                "description": term["description"],
                            }
                            break

    return link_id_map

def main() -> None:
    target_slug = None
    if "--syllabus" in sys.argv:
        idx = sys.argv.index("--syllabus")
        target_slug = sys.argv[idx + 1]

    slugs = [p.stem for p in GLOSSARY_SRC.glob("*.json")]
    if target_slug:
        slugs = [s for s in slugs if s == target_slug]
        if not slugs:
            print(f"No glossary file for: {target_slug}")
            sys.exit(1)
    slugs.sort()

    GLOSSARY_OUT.mkdir(parents=True, exist_ok=True)

    # Global id → term map (populated as we process each syllabus)
    all_map: dict = {}

    ok = skip = 0
    for slug in slugs:
        result = transform_syllabus(slug, all_map)
        if result is None:
            print(f"  skip  {slug}")
            skip += 1
            continue
        out = GLOSSARY_OUT / f"{slug}.json"
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        n = len(result["shared"]) + len(result["specific"])
        print(f"  ✓ {slug} ({len(result['shared'])} shared, {len(result['specific'])} specific)")
        ok += 1

    # Write global map (id → term for direct id lookups)
    MAP_OUT.write_text(json.dumps(all_map, indent=2, ensure_ascii=False) + "\n")

    # Build and write link-id map (data-item-id linkId → term)
    print("Building link-ID map from raw FA files...")
    from pathlib import Path as _Path
    content_dir = REPO_ROOT / "data" / "content"
    # Build slug_map from all_map (we already have id→term; build slug→term separately)
    slug_map: dict[str, dict] = {}
    for gf in GLOSSARY_SRC.glob("*.json"):
        try:
            raw_g = json.loads(gf.read_text())
            items_g = raw_g.get("pageProps", {}).get("data", {}).get("glossaries", {}).get("items", []) or []
            for item_g in items_g:
                el_g = item_g.get("elements", {})
                slug_g = el_g.get("slug", {}).get("value", "")
                desc_g = clean_html(el_g.get("description", {}).get("value", ""))
                title_g = el_g.get("title", {}).get("value", "").strip()
                if slug_g and title_g:
                    slug_map[slug_g] = {"title": title_g, "description": desc_g}
        except Exception:
            pass

    link_id_map = build_link_id_map(content_dir, slug_map)
    link_map_out = REPO_ROOT / "site" / "src" / "data" / "glossary-link-map.json"
    link_map_out.write_text(json.dumps(link_id_map, indent=2, ensure_ascii=False) + "\n")
    print()
    print(f"Done: {ok} written, {skip} skipped")
    print(f"Glossary map: {len(all_map)} unique terms → {MAP_OUT.name}")
    print(f"Link-ID map: {len(link_id_map)} linkIds resolved → {link_map_out.name}")


if __name__ == "__main__":
    main()
