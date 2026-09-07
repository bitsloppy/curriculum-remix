#!/usr/bin/env python3
"""
transform-content.py — Convert raw FA JSON → clean per-syllabus content JSON

Reads:  data/content/{slug}/{stage}/*.json
Writes: site/src/data/content/{slug}.json

Output shape per syllabus:
{
  "slug": "english-k-10-2022",
  "overview": "<html>...",                  // from overview.json
  "stages": [
    {
      "codename": "early_stage_1",
      "name": "Early Stage 1",
      "focusAreas": [
        {
          "codename": "fa4de39ca4",
          "title": "Oral language and communication",
          "outcomes": [{ "code": "ENe-OLC-01", "description": "<p>...</p>" }],
          "contentGroups": [
            {
              "title": "Listening for understanding",
              "items": [{ "text": "<p>...</p>", "examples": "<p>..." }]
            }
          ]
        }
      ]
    }
  ]
}

Usage:
  python3 scripts/transform-content.py                                  # all syllabuses
  python3 scripts/transform-content.py --syllabus english-k-10-2022    # one only
"""

import json
import sys
import re
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
CONTENT_DIR = REPO_ROOT / "data" / "content"
OUT_DIR = REPO_ROOT / "site" / "src" / "data" / "content"

EMPTY_HTML = {"<p><br></p>", "<p></p>", ""}

# Canonical stage order for display
STAGE_ORDER = [
    "early-stage-1",
    "stage-1",
    "stage-2",
    "stage-3",
    "stage-4",
    "stage-5",
    "year-11",
    "year-12",
    "stage-6",
    "life-skills",
]

# Map directory name → display name + codename
STAGE_META = {
    "early-stage-1": {"codename": "early_stage_1", "name": "Early Stage 1"},
    "stage-1":       {"codename": "stage_1",       "name": "Stage 1"},
    "stage-2":       {"codename": "stage_2",       "name": "Stage 2"},
    "stage-3":       {"codename": "stage_3",       "name": "Stage 3"},
    "stage-4":       {"codename": "stage_4",       "name": "Stage 4"},
    "stage-5":       {"codename": "stage_5",       "name": "Stage 5"},
    "year-11":       {"codename": "year_11",       "name": "Year 11"},
    "year-12":       {"codename": "year_12",       "name": "Year 12"},
    "stage-6":       {"codename": "stage_6",       "name": "Stage 6"},
    "life-skills":   {"codename": "life_skills",   "name": "Life Skills"},
}


def html_val(el: dict, key: str) -> str:
    raw = el.get(key, {}).get("value", "")
    if not isinstance(raw, str):
        return ""
    return raw if raw not in EMPTY_HTML else ""


def strip_kentico_refs(html: str) -> str:
    """Remove unresolved Kentico object placeholders."""
    return re.sub(
        r'<object[^>]+type="application/kenticocloud"[^>]*/?>(?:</object>)?',
        "",
        html,
    ).strip()


def resolve_overview(html: str, linked_items: dict) -> list[dict]:
    """
    Resolve Kentico object refs, then split on h4/h5 headings into sections.
    Each section: { heading, level (4|5|None), isAccordion, html }
    h5 sections become accordions; h4 sections are prose.
    """
    # ── Resolve <object> tags ──────────────────────────────────────────────────
    def resolve_obj(match: re.Match) -> str:
        cn_match = re.search(r'data-codename="([^"]+)"', match.group(0))
        if not cn_match:
            return ""
        cn = cn_match.group(1)
        item = linked_items.get(cn, {})
        if not item:
            return ""
        sys_type = item.get("system", {}).get("type", "")
        el = item.get("elements", {})

        if sys_type == "contentrichtext":
            content = el.get("content", {}).get("value", "")
            if content and content not in EMPTY_HTML:
                return strip_kentico_refs(content)
            return ""

        if sys_type == "ui_media":
            caption = el.get("caption", {}).get("value", "")
            if caption:
                return f'<p class="fig-caption">{caption}</p>'
            return ""

        if sys_type == "ui_accordion":
            # Render each accordion_item as a nested detail/summary
            item_codenames = el.get("items", {}).get("value", [])
            parts = []
            for acc_cn in item_codenames:
                acc = linked_items.get(acc_cn, {})
                acc_el = acc.get("elements", {})
                acc_title = acc_el.get("title", {}).get("value", "")
                acc_content = acc_el.get("content", {}).get("value", "")
                if acc_title or acc_content:
                    parts.append(
                        f'<details class="nested-acc">'
                        f'<summary>{acc_title}</summary>'
                        f'{acc_content}'
                        f'</details>'
                    )
            return "\n".join(parts)

        if sys_type == "accordion_item":
            acc_title = el.get("title", {}).get("value", "")
            acc_content = el.get("content", {}).get("value", "")
            if acc_title or acc_content:
                return (
                    f'<details class="nested-acc">'
                    f'<summary>{acc_title}</summary>'
                    f'{acc_content}'
                    f'</details>'
                )
            return ""

        return ""

    resolved = re.sub(
        r'<object[^>]+type="application/kenticocloud"[^>]*/?>(?:</object>)?',
        resolve_obj,
        html,
    )

    # ── Split on h4 / h5 headings ──────────────────────────────────────────────
    heading_re = re.compile(r'<(h[45])[^>]*>(.*?)</h[45]>', re.DOTALL)
    sections: list[dict] = []
    last_end = 0
    pending_heading = None
    pending_level = None
    pending_html = ""

    def flush(next_heading=None, next_level=None):
        nonlocal pending_heading, pending_level, pending_html
        body = pending_html.strip()
        if body or pending_heading:
            sections.append({
                "heading": pending_heading,
                "level": pending_level,
                "isAccordion": pending_level == 5,
                "html": body,
            })
        pending_heading = next_heading
        pending_level = next_level
        pending_html = ""

    for m in heading_re.finditer(resolved):
        pending_html += resolved[last_end : m.start()]
        flush(
            next_heading=re.sub(r'<[^>]+>', '', m.group(2)).strip(),
            next_level=int(m.group(1)[1]),
        )
        last_end = m.end()

    pending_html += resolved[last_end:]
    flush()

    return [s for s in sections if s["heading"] or s["html"]]


def transform_syllabus(slug: str) -> dict | None:
    syl_dir = CONTENT_DIR / slug
    if not syl_dir.exists():
        return None

    overview_path = syl_dir / "overview.json"
    if not overview_path.exists():
        return None

    # ── Overview HTML + sections ──────────────────────────────────────────────────
    overview_raw = json.loads(overview_path.read_text())
    pp = overview_raw.get("pageProps", {}).get("data", {})
    syl_li = pp.get("syllabus", {}).get("linkedItems", {})
    syl_el = pp.get("syllabus", {}).get("item", {}).get("elements", {})
    overview_html_raw = html_val(syl_el, "web_content_rtb__content")
    overview_html = strip_kentico_refs(overview_html_raw)  # fallback
    overview_sections = resolve_overview(overview_html_raw, syl_li)

    # ── Rationale + Aim HTML ────────────────────────────────────────────────────
    rationale_html = ""
    rationale_path = syl_dir / "rationale.json"
    if rationale_path.exists():
        rat_raw = json.loads(rationale_path.read_text())
        rat_el = (
            rat_raw.get("pageProps", {})
            .get("data", {})
            .get("syllabus", {})
            .get("item", {})
            .get("elements", {})
        )
        rationale_html = strip_kentico_refs(html_val(rat_el, "rationale"))

    aim_html = ""
    aim_path = syl_dir / "aim.json"
    if aim_path.exists():
        aim_raw = json.loads(aim_path.read_text())
        aim_el = (
            aim_raw.get("pageProps", {})
            .get("data", {})
            .get("syllabus", {})
            .get("item", {})
            .get("elements", {})
        )
        aim_html = strip_kentico_refs(html_val(aim_el, "aim"))

    # ── Stage directories in canonical order ──────────────────────────────────
    stage_dirs = {}
    for d in syl_dir.iterdir():
        if d.is_dir() and d.name in STAGE_META:
            stage_dirs[d.name] = d

    stages_out = []
    overarching_seen: dict[str, dict] = {}  # codename → {code, description}

    # Detect year-11/year-12 dirs that are genuine (different FAs from life-skills).
    # For LS syllabuses, year-11/ year-12/ stage-6/ all point to the same FA IDs as
    # life-skills/ — treat them as duplicates and skip.
    def fa_ids_in(d: Path) -> frozenset[str]:
        return frozenset(f.stem for f in d.glob("*.json"))

    ls_ids = fa_ids_in(stage_dirs["life-skills"]) if "life-skills" in stage_dirs else frozenset()
    s6_ids = fa_ids_in(stage_dirs["stage-6"]) if "stage-6" in stage_dirs else frozenset()
    y11_ids = fa_ids_in(stage_dirs["year-11"]) if "year-11" in stage_dirs else frozenset()
    y12_ids = fa_ids_in(stage_dirs["year-12"]) if "year-12" in stage_dirs else frozenset()
    has_real_year_dirs = bool(y11_ids and y11_ids != ls_ids) or bool(y12_ids and y12_ids != ls_ids)
    # stage-6 is a LS duplicate when it shares its single entry FA with life-skills
    s6_is_ls_dupe = bool(s6_ids and ls_ids and s6_ids.issubset(ls_ids | y11_ids | y12_ids) and s6_ids & ls_ids)

    for stage_slug in STAGE_ORDER:
        if stage_slug not in stage_dirs:
            continue
        # Skip stage-6 when real year dirs exist (stage-6 = LS duplicate in Stage 6 syllabuses)
        # Also skip when stage-6 is a pure LS duplicate (entry FA same as life-skills)
        # Skip stage-6 when year-11/12 dirs exist (LS dupe) OR when life-skills dir exists
        # (for LS-only syllabuses, defaultFocusAreaUrls.stage_6 → same FA as life-skills)
        if stage_slug == "stage-6" and ("life-skills" in stage_dirs or has_real_year_dirs):
            continue
        # Skip year-11/year-12 when they are duplicates of life-skills (LS syllabuses)
        if stage_slug == "year-11" and y11_ids == ls_ids:
            continue
        if stage_slug == "year-12" and y12_ids == ls_ids:
            continue
        stage_dir = stage_dirs[stage_slug]
        meta = STAGE_META[stage_slug]

        # Each .json file = one focus area
        fa_files = sorted(stage_dir.glob("*.json"))
        if not fa_files:
            continue

        focus_areas_out = []
        seen_fa_codenames = set()

        for fa_path in fa_files:
            raw = json.loads(fa_path.read_text())
            fa_pp = raw.get("pageProps", {}).get("data", {})
            fa_obj = fa_pp.get("focusArea", {})
            fa_item = fa_obj.get("item", {})
            if not fa_item:
                continue
            li = fa_obj.get("linkedItems", {})

            fa_sys = fa_item.get("system", {})
            fa_codename = fa_sys.get("codename", fa_path.stem)
            if fa_codename in seen_fa_codenames:
                continue
            seen_fa_codenames.add(fa_codename)

            fa_el = fa_item.get("elements", {})
            fa_title = html_val(fa_el, "title") or fa_codename

            # ── Outcomes ──────────────────────────────────────────────────────
            syl_li = fa_pp.get("syllabus", {}).get("linkedItems", {})
            outcomes_out = []
            for oc_cn in fa_el.get("outcomes", {}).get("value", []):
                oc = li.get(oc_cn) or syl_li.get(oc_cn, {})
                oc_el = oc.get("elements", {})
                code = oc_el.get("code", {}).get("value", "")
                desc = strip_kentico_refs(html_val(oc_el, "description"))
                is_overarching = any(
                    v.get("codename") == "yes"
                    for v in oc_el.get("isoverarching", {}).get("value", [])
                )
                if code or desc:
                    if is_overarching:
                        overarching_seen[oc_cn] = {"code": code, "description": desc}
                    else:
                        outcomes_out.append({"code": code, "description": desc})

            # ── Content groups ────────────────────────────────────────────────
            cg_codenames = fa_el.get("contentgroups", {}).get("value", [])
            cgs_out = []
            for cg_cn in cg_codenames:
                cg = li.get(cg_cn, {})
                cg_el = cg.get("elements", {})
                cg_title = html_val(cg_el, "title")

                # Skip "Complementary content" groups (accessibility variants)
                if cg_title.lower().startswith("complementary content"):
                    continue

                items_out = []
                for ci_cn in cg_el.get("content_items", {}).get("value", []):
                    ci = li.get(ci_cn, {})
                    ci_el = ci.get("elements", {})
                    text = strip_kentico_refs(html_val(ci_el, "title"))
                    examples = strip_kentico_refs(html_val(ci_el, "examples"))
                    if text:
                        items_out.append({"text": text, "examples": examples})

                if items_out or cg_title:
                    cgs_out.append({"title": cg_title, "items": items_out})

            focus_areas_out.append({
                "codename": fa_codename,
                "title": fa_title,
                "outcomes": outcomes_out,
                "contentGroups": cgs_out,
            })

        # ── Supplementary pass: fill missing FAs from stageFocusAreas ────────
        # Handles stages (e.g. life-skills) where only 1 file is fetched but
        # stageFocusAreas contains all focus areas. Outcomes are resolved from
        # syllabus.linkedItems which is always fully populated.
        seen_titles = {fa["title"] for fa in focus_areas_out}
        raw2 = json.loads(fa_path.read_text())
        fa_pp2 = raw2.get("pageProps", {}).get("data", {})
        sfas = fa_pp2.get("stageFocusAreas", [])
        syl_li = fa_pp2.get("syllabus", {}).get("linkedItems", {})

        for sfa in sfas:
            sfa_el = sfa.get("elements", {})
            sfa_title = sfa_el.get("title", {}).get("value", "").strip()
            if not sfa_title or sfa_title in seen_titles:
                continue
            seen_titles.add(sfa_title)

            # Outcomes
            sfa_outcomes: list[dict] = []
            for oc_cn in sfa_el.get("outcomes", {}).get("value", []):
                oc = syl_li.get(oc_cn, {})
                oc_el = oc.get("elements", {})
                code = oc_el.get("code", {}).get("value", "")
                desc = strip_kentico_refs(html_val(oc_el, "description"))
                if code or desc:
                    sfa_outcomes.append({"code": code, "description": desc})

            # Content groups
            sfa_cgs: list[dict] = []
            for cg_cn in sfa_el.get("contentgroups", {}).get("value", []):
                cg = syl_li.get(cg_cn, {})
                cg_el = cg.get("elements", {})
                cg_title = html_val(cg_el, "title")
                if cg_title.lower().startswith("complementary content"):
                    continue
                cg_items: list[dict] = []
                for ci_cn in cg_el.get("content_items", {}).get("value", []):
                    ci = syl_li.get(ci_cn, {})
                    ci_el = ci.get("elements", {})
                    text = strip_kentico_refs(html_val(ci_el, "title"))
                    examples = strip_kentico_refs(html_val(ci_el, "examples"))
                    if text:
                        cg_items.append({"text": text, "examples": examples})
                if cg_items or cg_title:
                    sfa_cgs.append({"title": cg_title, "items": cg_items})

            if sfa_outcomes or sfa_cgs:
                safe = sfa_title.lower().replace(" ", "_").replace(",", "")
                focus_areas_out.append({
                    "codename": f"sfa_ls_{safe}",
                    "title": sfa_title,
                    "outcomes": sfa_outcomes,
                    "contentGroups": sfa_cgs,
                })

        if focus_areas_out:
            stages_out.append({
                "codename": meta["codename"],
                "name": meta["name"],
                "focusAreas": focus_areas_out,
            })

    return {
        "slug": slug,
        "overview": overview_html,
        "overviewSections": overview_sections,
        "rationale": rationale_html,
        "aim": aim_html,
        "overarchingOutcomes": list(overarching_seen.values()),
        "stages": stages_out,
    }


def main() -> None:
    target_slug = None
    if "--syllabus" in sys.argv:
        idx = sys.argv.index("--syllabus")
        target_slug = sys.argv[idx + 1]

    syllabuses = json.loads((CONTENT_DIR / "syllabuses.json").read_text())
    targets = [s["slug"] for s in syllabuses]
    if target_slug:
        targets = [s for s in targets if s == target_slug]
        if not targets:
            print(f"Not found: {target_slug}")
            sys.exit(1)

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ok = err = skip = 0
    for slug in targets:
        result = transform_syllabus(slug)
        if result is None:
            print(f"  skip  {slug}")
            skip += 1
            continue
        if not result["stages"]:
            print(f"  empty {slug}")
            skip += 1
            # Still write an empty file so the page can detect no-content state
            (OUT_DIR / f"{slug}.json").write_text(
                json.dumps(result, indent=2, ensure_ascii=False) + "\n"
            )
            continue
        out_path = OUT_DIR / f"{slug}.json"
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
        n_fas = sum(len(s["focusAreas"]) for s in result["stages"])
        print(f"  ✓ {slug}  ({len(result['stages'])} stages, {n_fas} FAs)")
        ok += 1

    print(f"\nDone: {ok} written, {skip} skipped/empty, {err} errors")


if __name__ == "__main__":
    main()
