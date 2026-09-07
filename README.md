# curriculum-remix

A display website that pulls structured curriculum data from [curriculum.nsw.edu.au](https://curriculum.nsw.edu.au) and presents it in a more navigable, cross-linked format — with a focus on outcomes browsing by stage and KLA.

**Live site:** https://curriculum-remix.bitsloppy.com

**Stack:** Astro 7 + Web Awesome Pro 3.12 · Python 3 data pipeline · Cloudflare Pages

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
│   ├── fetch-content.py       # Fetches all syllabus content
│   └── transform-content.py   # Converts raw JSON → clean per-syllabus content JSON
│
├── data/
│   ├── state.json             # Tracks current build ID + last fetch timestamp
│   ├── snapshots/             # KLA-level snapshots (from fetch-data.py)
│   │   └── YYYY-MM-DD_HHmmss_<build-id>/
│   └── content/               # Per-syllabus raw JSON (from fetch-content.py)
│       └── {syllabus-slug}/
│
└── site/                      # Astro display website
    ├── .npmrc                 # Private registry config for WA Pro (token via env var)
    └── src/
        ├── data/
        │   ├── syllabuses.json           # Site syllabus list (88 entries, source of truth)
        │   ├── content/{slug}.json       # Transformed content per syllabus
        │   ├── course-descriptions.json  # 171 course descriptions
        │   └── glossary-map.json         # 2,499 glossary terms
        ├── layouts/
        │   └── Layout.astro
        └── pages/
            ├── index.astro
            ├── primary/index.astro       # K–6 outcomes by stage
            ├── secondary/index.astro     # 7–10 outcomes with KLA tabs
            ├── syllabuses/
            │   ├── index.astro           # Syllabus list with filters
            │   └── [slug].astro          # Syllabus detail (outcomes view)
            └── course-descriptions/
                └── index.astro
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

# Batches
python3 scripts/fetch-content.py --offset 0 --limit 10
```

Run from the `site/` directory using the local venv: `.venv/bin/python3 ../scripts/fetch-content.py`.

**What's fetched:** 88 syllabuses. 8 legacy CEC syllabuses and 11 Stage 6 syllabuses (not yet published by NESA) have no content.

### Step 3 — Transform to site-ready JSON

```bash
python3 scripts/transform-content.py                                  # all syllabuses
python3 scripts/transform-content.py --syllabus english-k-10-2022    # one only
```

Reads from `data/content/`, writes to `site/src/data/content/`.

Produces a clean JSON per syllabus:
```json
{
  "slug": "english-k-10-2022",
  "overarchingOutcomes": [{ "code": "...", "description": "..." }],
  "stages": [
    {
      "codename": "early_stage_1",
      "name": "Early Stage 1",
      "focusAreas": [
        {
          "title": "Phonological awareness",
          "outcomes": [{ "code": "ENe-PHOAW-01", "description": "..." }]
        }
      ]
    }
  ]
}
```

---

## Syllabus list (`site/src/data/syllabuses.json`)

**Source of truth.** Derived from the live curriculum.nsw.edu.au site. 88 entries.

Key fields: `slug`, `name`, `kla`, `klaLabel`, `stage`, `type` (MS/LS), `hasContent`, `curriculumUrl`.

---

## Site pages

### `/` — Home
Browse by KLA. Links to syllabuses list pre-filtered by KLA.

### `/syllabuses` — Syllabus index
Filterable table. KLA dropdown + stage/type chips. Sticky header.

### `/syllabuses/[slug]` — Syllabus detail
Outcomes-only view. Outcomes grouped by focus area, displayed in stage columns. Syllabuses with overarching outcomes (Maths only — MAO-WM-01) show a sticky overarching bar above the stage columns.

Zero-content syllabuses (8 CEC legacy + 11 unpublished Stage 6) show a "not yet available" state.

### `/primary` — Primary K–6
All K–6 outcomes across all KLAs, organised by stage (ES1 / S1 / S2 / S3). Languages KLAs hidden by default with opt-in toggle chips.

### `/secondary` — Secondary 7–10
Outcomes for all 33 secondary syllabuses. KLA tabs (English / Maths / Science / TAS / HSIE / Creative Arts / PDHPE / Languages). Stage selector (Stage 4 / Stage 5) with additive Life Skills toggle. Per-syllabus opt-out chips.

### `/course-descriptions` — Course descriptions
171 courses with stage, type, hours, aligned syllabus, and link to the NSW Curriculum site. Sticky filter bar + sticky table header.

---

## Build and deploy

```bash
cd site
WEBAWESOME_NPM_TOKEN="..." npm install   # first time — needs the WA Pro token
npm run build                            # 93 pages, ~400ms
npm run dev                              # dev server (Anna runs this herself)
```

**Deploy:** `git push origin main` → GitHub Actions → Cloudflare Pages (~90s).

### Web Awesome Pro setup

WA Pro is installed from a private Cloudsmith registry. The `site/.npmrc` is committed and uses an environment variable for the token:

```
@web.awesome.me:registry=https://npm.cloudsmith.io/fortawesome/webawesome-pro/
//npm.cloudsmith.io/fortawesome/webawesome-pro/:_authToken=${WEBAWESOME_NPM_TOKEN}
```

GitHub Actions uses the `WA_TOKEN` repo secret as `WEBAWESOME_NPM_TOKEN`. For local installs, set the env variable before running `npm install`.

WA components are imported explicitly in `Layout.astro` (no CDN, no autoloader — Vite bundles everything at build time). FA Pro icons (including `turntable`) are unlocked via `data-fa-kit-code` on `<html>`.

### GitHub Actions secrets required

| Secret | Purpose |
|---|---|
| `CLOUDFLARE_API_TOKEN` | Cloudflare Pages deploy (Pages: Edit permission) |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account |
| `WA_TOKEN` | WA Pro npm registry token |

---

## Design tokens

### Brand

```css
--site-brand:      #3e1547;  /* brand purple — header, nav */
--site-brand-text: #ffffff;
--font-display:    'Sedgwick Ave Display', cursive;
--font-ui:         'Outfit', system-ui, sans-serif;
```

### KLA colours

```css
--kla-english:       #be123c;  /* rose-700 */
--kla-mathematics:   #0f766e;  /* teal-700 */
--kla-science:       #0369a1;  /* sky-700 */
--kla-tas:           #b45309;  /* amber-700 */
--kla-hsie:          #7c3aed;  /* violet-700 */
--kla-creative-arts: #be185d;  /* pink-700 */
--kla-pdhpe:         #15803d;  /* green-700 */
--kla-languages:     #0e7490;  /* cyan-700 */
--kla-vet:           #9333ea;  /* purple-700 */
```

---

## Known gaps / next steps

- **Lock file:** `package-lock.json` is out of sync with WA Pro. Run `npm install` locally with the token and commit the updated lock, then switch the workflow back to `npm ci`.
- **Favicon:** Not yet added.
- **Deferred content:** Overview, Aim/Rationale, Content, and Glossary tab content was built but removed from the current scope. Code is preserved at git commit `eeef6d7`.
- **Stage 6 content:** 11 syllabuses have no content — NESA hasn't published it yet. Re-run `fetch-content.py` periodically.
- **ACARA code mapping:** Phase 3 — cross-referencing NSW outcome codes to Australian Curriculum codes. Not started.
- **Search:** No search yet. Outcome codes and content items are all in the transformed JSON and could feed a client-side index (Pagefind or Fuse.js).

---

## Python environment

```bash
cd curriculum-remix
python3 -m venv .venv
source .venv/bin/activate
pip install requests
```
