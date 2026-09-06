# Curriculum Remix — AGENTS.md

Build operations guide for AI agents working on this project.

---

## Current phase: Phase 3 — ACARA Code Mapping (not started)

Phases 1 (data pipeline) and 2 (display website) are complete.
Phase 3 maps NSW outcome codes to Australian Curriculum (ACARA) codes.

**Before starting any work:** read this file and `PROJECT.md` to confirm what's in scope.

---

## What this project is

A display website that remixes NSW curriculum data from curriculum.nsw.edu.au into a more
navigable, cross-linked format — with Australian Curriculum (ACARA) code mapping layered on top.

- **Repo:** `~/code/curriculum-remix` → https://github.com/bitsloppy/curriculum-remix
- **Live site:** https://curriculum-remix.pages.dev
- **Git identity:** always use Bit Sloppy / hello@bitsloppy.com (local repo config already set)

---

## Agent roles

| Agent | Role | Active phase |
|---|---|---|
| Good Buddy 🦉 | Orchestration, planning, memory | All phases |
| Ninja 🥷 | Site code (Astro + Web Awesome), data pipeline | All phases |

---

## Tech stack

- **Site:** Astro 4 + Web Awesome 3, deployed to Cloudflare Pages
- **Data pipeline:** Python 3 scripts in `scripts/` at repo root
- **Deployment:** GitHub Actions → Cloudflare Pages (auto on push to `main`)

---

## Build plan

| Phase | Task | Status |
|---|---|---|
| **1** | Data pipeline (fetch + transform) | ✅ Done |
| **2** | Display website (all core pages, filters, glossary) | ✅ Done |
| **3** | ACARA code mapping (DOCX extraction + ACARA API) | ⬜ Not started |
| **4** | Missing content (assessment + glossary pages; zero-content Stage 6) | ⬜ Not started |
| **5** | Discovery features (cross-ref view, outcome decoder, timeline, search) | ⬜ Not started |
| **6** | Automation (scheduled build-ID check + auto re-fetch via GitHub Actions) | ⬜ Not started |

See `PROJECT.md` for full phase detail and feature lists.

---

## Key file paths

| Resource | Path |
|---|---|
| Repo root | `~/code/curriculum-remix/` |
| Project plan | `PROJECT.md` |
| Data pipeline scripts | `scripts/` |
| Raw snapshots | `data/snapshots/<timestamp>_<build-id>/` |
| Transformed content JSON | `data/content/` |
| Glossary JSON | `data/glossary/` |
| Site code | `site/` |
| Syllabus list (source of truth) | `site/src/data/syllabuses.json` |
| Per-syllabus content data | `site/src/data/content/{slug}.json` |
| Course descriptions | `site/src/data/course-descriptions.json` |
| Glossary map (UUID → term) | `site/src/data/glossary-map.json` |
| Design tokens | `site/src/lib/tokens.ts` |
| Icon map | `site/src/lib/icons.ts` |
| Web Awesome skill docs | `site/node_modules/@awesome.me/webawesome/dist/skills/` |

---

## Data state

- **88 syllabuses** — authoritative list in `site/src/data/syllabuses.json`
  - 69 with full content fetched and transformed
  - 8 legacy CEC (no content in new system)
  - 11 Stage 6 not yet published by NESA
- **91 pages building, 0 errors** (as of 2026-08-02)
- **171 course descriptions** in `site/src/data/course-descriptions.json`
- **2,499 glossary terms** in `site/src/data/glossary-map.json`

---

## Running the data pipeline

```bash
# Fetch build ID + KLA snapshots (skips if build ID unchanged)
python3 scripts/fetch-data.py

# Fetch all syllabus content pages (run from site/ dir)
cd site && .venv/bin/python3 ../scripts/fetch-content.py

# Transform raw JSON → site data files
.venv/bin/python3 ../scripts/transform-content.py
```

Always `--dry-run` flag scripts that modify existing data before committing.

## Running the site

```bash
cd site
npm run dev      # local dev server
npm run build    # production build check
git push origin main   # triggers Cloudflare Pages deploy
```

---

## Key invariants (don't break these)

1. **`site/src/data/syllabuses.json` is the source of truth** for the syllabus list — 88 entries. Never hand-edit; it's generated from the live site.
2. **Git identity.** Always commit as Bit Sloppy / hello@bitsloppy.com.
3. **Web Awesome token scale is reversed from Tailwind.** `neutral-50` = mid-dark grey; `neutral-95` = very light. Valid steps: 05, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95. See Ninja's MEMORY.md for the full mapping.
4. **WA layout classes, not custom elements.** `<div class="wa-stack">` not `<wa-stack>`.
5. **Anna runs `npm run dev` herself.** Don't start the dev server unless asked.

---

*Update the Build Plan table when phases change.*
*Last updated: 2026-08-21*
