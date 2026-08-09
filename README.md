# curriculum-remix

A display website that pulls structured curriculum data from [curriculum.nsw.edu.au](https://curriculum.nsw.edu.au) and presents it in a more navigable, cross-linked format.

**Stack:** Astro 4 + Web Awesome 3 · Python 3 data pipeline · Cloudflare Pages

---

## How the source data works

`curriculum.nsw.edu.au` is a Next.js app backed by a Kentico Kontent CMS. Every page pre-renders its data as a JSON file at:

```
https://curriculum.nsw.edu.au/_next/data/<build-id>/<slug>.json
```

The build ID changes with each Vercel deployment. The fetch scripts detect and track it automatically.

Each JSON file has a `pageProps.data` object containing Kentico content items. Each item has:

- **`system`** — `codename`, `id`, `type`, `lastModified`
- **`elements`** — typed fields: `text`, `rich_text`, `taxonomy`, `modular_content`
- **`linkedItems`** — resolved referenced items (outcomes, content groups, content items, etc.)

---

## Project structure

```
curriculum-remix/
├── scripts/
│   ├── fetch-data.py          # Fetches KLA-level snapshot pages
│   ├── fetch-content.py       # Fetches all syllabus content (FA pages, overview, aim, rationale)
│   └── transform-content.py   # Converts raw JSON → clean per-syllabus content JSON
│
├── data/
│   ├── state.json             # Tracks current build ID + last fetch timestamp
│   ├── syllabuses-raw.csv     # Original CSV data (superseded by live site list)
│   ├── snapshots/             # KLA-level snapshots (from fetch-data.py)
│   │   └── YYYY-MM-DD_HHmmss_<build-id>/
│   │       ├── learning-areas.json
│   │       ├── english.json
│   │       └── ...
│   └── content/               # Per-syllabus raw JSON (from fetch-content.py) — 7.6 GB
│       ├── syllabuses.json    # Authoritative syllabus list (88 entries, source of truth)
│       └── {syllabus-slug}/
│           ├── overview.json
│           ├── rationale.json
│           ├── aim.json
│           └── {stage-slug}/
│               └── {fa-id}.json
│
└── site/                      # Astro display website
    └── src/
        ├── data/
        │   ├── syllabuses.json           # Site syllabus list (cleaned, from syllabuses.json)
        │   └── content/
        │       └── {syllabus-slug}.json  # Transformed content (from transform-content.py)
        ├── layouts/
        │   └── Layout.astro
        └── pages/
            ├── index.astro
            └── syllabuses/
                ├── index.astro           # Syllabus list with filters
                └── [slug].astro          # Syllabus detail page
```

---

## Data pipeline

### Step 1 — Fetch KLA snapshots (one-time / on build-ID change)

```bash
python3 scripts/fetch-data.py           # skip if build unchanged
python3 scripts/fetch-data.py --force   # always fetch
```

Saves 10 KLA overview pages to `data/snapshots/`.

### Step 2 — Fetch syllabus content

```bash
# All 88 syllabuses (slow — ~30–40 min, rate-limited at 0.5s/req)
python3 scripts/fetch-content.py

# Single syllabus
python3 scripts/fetch-content.py --syllabus english-k-10-2022

# Batches (recommended for first run)
python3 scripts/fetch-content.py --offset 0  --limit 10
python3 scripts/fetch-content.py --offset 10 --limit 10
# ... etc.

# Force re-fetch even if build ID unchanged
python3 scripts/fetch-content.py --force
```

For each syllabus, saves:
- `overview.json` — syllabus overview page (organisation, focus area discovery)
- `rationale.json` — rationale page
- `aim.json` — aim page
- `{stage}/{fa-id}.json` — one file per focus area per stage

Uses a virtualenv at `curriculum-remix/.venv` (needs `requests`).

**What's fetched:** 88 syllabuses · ~1,768 JSON files · 7.6 GB raw

**Zero-content syllabuses (19):** 8 legacy CEC syllabuses (pre-2010, no content in the new system) + 11 Stage 6 syllabuses not yet published on curriculum.nsw.edu.au (English Advanced, EAL/D, Maths Extension 1/2/Advanced, Economics, History Extension, Music 2, Music Extension, Software Engineering).

### Step 3 — Transform to site-ready JSON

```bash
python3 scripts/transform-content.py                                  # all syllabuses
python3 scripts/transform-content.py --syllabus english-k-10-2022    # one only
```

Reads from `data/content/`, writes to `site/src/data/content/`.

For each syllabus produces a clean JSON with:
```json
{
  "slug": "english-k-10-2022",
  "overview": "<html>...",
  "overviewSections": [
    { "heading": "Organisation of English K–10", "level": 4, "isAccordion": false, "html": "..." },
    { "heading": "K–2 focus areas",              "level": 5, "isAccordion": true,  "html": "..." },
    ...
  ],
  "rationale": "<html>...",
  "aim": "<html>...",
  "stages": [
    {
      "codename": "early_stage_1",
      "name": "Early Stage 1",
      "focusAreas": [
        {
          "codename": "fa4de39ca4",
          "title": "Phonological awareness",
          "outcomes": [{ "code": "ENe-PHOAW-01", "description": "<p>...</p>" }],
          "contentGroups": [
            {
              "title": "Words",
              "items": [{ "text": "<p>...</p>", "examples": "<p>...</p>" }]
            }
          ]
        }
      ]
    }
  ]
}
```

**Kentico object resolution:** `<object type="application/kenticocloud">` tags in rich text are resolved at transform time:
- `contentrichtext` → inline HTML
- `ui_media` → figure caption text
- `ui_accordion` / `accordion_item` → native `<details>` elements

**Overview sections:** Split on `<h4>` and `<h5>` tags. `<h5>` sections (focus area groups: K–2, 3–6, 7–10, Text requirements) become accordions. `<h4>` sections become prose.

---

## Syllabus list (`data/content/syllabuses.json`)

**This is the source of truth.** It's derived from the live curriculum.nsw.edu.au site (88 syllabuses). Anything not in this list is no longer published.

Fields per entry:
| Field | Description |
|---|---|
| `slug` | Canonical URL slug (matches curriculum.nsw.edu.au path) |
| `name` | Full syllabus name |
| `kla` | KLA codename (`english`, `mathematics`, `hsie`, etc.) |
| `klaLabel` | Display label |
| `contentModel` | `reformed` (standard) or `course-based` |
| `publicationYear` | e.g. `"2022"` |
| `doredirect` | Whether the syllabus is a redirect alias |
| `lastModified` | ISO timestamp of last Kentico update |

The site's `syllabuses.json` (`site/src/data/syllabuses.json`) extends this with:
| Field | Description |
|---|---|
| `stage` | Derived stage range: `K–6`, `K–10`, `7–10`, `7–8`, `11–12` |
| `type` | `MS` (Mainstream) or `LS` (Life Skills) |
| `hasContent` | Whether content pages were found |
| `contentPages` | Count of focus area JSON files |
| `curriculumUrl` | Full URL on curriculum.nsw.edu.au |
| `nesaUrl` | Legacy NESA URL (where available) |
| `isMandatory` / `isElective` | Classification (where available from old CSV data) |

---

## Site pages

### `/` — Home
KLA cards linking to the syllabuses list pre-filtered by KLA.

### `/syllabuses` — Syllabus index
Filter bar with KLA dropdown and stage/type chips. All 88 syllabuses. Cards show KLA chip, Life Skills badge, and "Live on curriculum.nsw.edu.au" indicator for content syllabuses.

### `/syllabuses/[slug]` — Syllabus detail

Tabs:
| Tab | Content | Source |
|---|---|---|
| **Overview** | Syllabus organisation, focus area accordions (K–2, 3–6, 7–10), contextual sections | `overviewSections` |
| **Aim and rationale** | Aim statement + full rationale | `aim`, `rationale` |
| **Outcomes** | All outcomes per stage, grouped by focus area | `stages[].focusAreas[].outcomes` |
| **Content** | Focus areas as collapsible panels; content groups + items with examples | `stages[].focusAreas[].contentGroups` |
| **Assessment** | Placeholder → links to curriculum.nsw.edu.au | — |
| **Glossary** | Placeholder → links to curriculum.nsw.edu.au | — |

**Stage selector:** Sticky `wa-select` above the tabs. Switching stage shows/hides `.stage-section[data-stage]` elements across Outcomes and Content tabs simultaneously via `wa-change` JS event.

Zero-content syllabuses (the 19 without fetched pages) show a "not yet available" state with a link to the live site.

---

## Build

```bash
cd site
npm install
npm run build   # 90 pages, ~350ms
npm run dev     # dev server
```

**Deploy:** `git push origin main` → GitHub Actions → Cloudflare Pages.

---

## KLA colour tokens

```css
--kla-english:       #1d4ed8;  /* blue */
--kla-mathematics:   #7c3aed;  /* violet */
--kla-science:       #059669;  /* emerald */
--kla-tas:           #d97706;  /* amber */
--kla-hsie:          #dc2626;  /* red */
--kla-creative-arts: #db2777;  /* pink */
--kla-pdhpe:         #0891b2;  /* cyan */
--kla-languages:     #65a30d;  /* lime */
--kla-vet:           #64748b;  /* slate */
```

---

## Known gaps / next steps

- **Assessment + Glossary tabs:** These are separate page endpoints (`/assessment`, `/glossary`) not yet fetched. Same pattern as aim/rationale — add to `fetch-content.py`, extract in transformer.
- **Glossary term links:** Content items contain `<a data-item-id="..." href="">` tags pointing to glossary entries with empty hrefs. Could resolve to actual glossary terms when glossary is fetched.
- **Stage 6 content:** 11 syllabuses show 0 pages — NESA hasn't published their content yet. Re-run `fetch-content.py` periodically.
- **Build-ID change detection:** The `fetch-data.py` script tracks the KLA snapshot build ID. `fetch-content.py` doesn't update `state.json` for partial runs — run without `--offset`/`--limit`/`--syllabus` to update state after a full fetch.
- **Outcomes cross-reference:** Outcome codes are extracted per-syllabus but not yet cross-linked (e.g. no "all Stage 3 outcomes across all KLAs" view).
- **Search:** No search yet. Outcome codes and content items are all in the transformed JSON and could feed a client-side index (Pagefind or Fuse.js).

---

## Python environment

```bash
cd curriculum-remix
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```

Scripts use `#!/usr/bin/env python3` and expect the venv to be active, or be run directly via `.venv/bin/python3 scripts/...`.
