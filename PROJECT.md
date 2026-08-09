# Curriculum Remix — Project Plan

**What:** A display website that remixes NSW curriculum data from curriculum.nsw.edu.au into a more navigable, cross-linked format — with Australian Curriculum (ACARA) code mapping layered on top.

**Repo:** https://github.com/bitsloppy/curriculum-remix
**Started:** 2026-07-23

---

## Feature List

### 🗄️ Phase 1 — Data Pipeline ✅

- [x] Detect current Next.js build ID from homepage HTML
- [x] Fetch all 10 KLA pages as structured JSON (Next.js data endpoints)
- [x] Store versioned snapshots in `data/snapshots/<timestamp>_<build-id>/`
- [x] Skip fetch if build ID unchanged; `--force` flag to override
- [x] GitHub repo live at bitsloppy/curriculum-remix
- [x] Discover authoritative syllabus list from live site (88 syllabuses)
- [x] Fetch all focus-area content pages per syllabus (`fetch-content.py`)
  - `--syllabus`, `--offset`, `--limit` flags for targeted/batched runs
  - Fetches overview, rationale, aim + all stage/FA pages per syllabus
  - 88 syllabuses · 1,768 JSON files · 7.6 GB raw
- [x] Transform raw JSON → clean per-syllabus content JSON (`transform-content.py`)
  - Resolves Kentico `<object>` refs (contentrichtext, ui_media, ui_accordion)
  - Extracts: aim, rationale, overview sections, outcomes, content groups + items
  - `overviewSections` splits on h4/h5 headings; h5 → accordion, h4 → prose
- [x] `site/src/data/syllabuses.json` — 88-entry authoritative list synced from live site
  - Replaces old 114-entry CSV-derived list
  - Adds `hasContent`, `contentPages`, `stage` (derived), `type` (MS/LS), `curriculumUrl`

### 🌐 Phase 2 — Display Website ✅ (in progress)

- [x] Framework: Astro 4 + Web Awesome 3
- [x] Home page — 9 KLA cards linking to pre-filtered syllabus list
- [x] Syllabus list (`/syllabuses`) — filter bar (KLA dropdown + stage/type chips), 88 syllabuses, content indicator badge
- [x] Syllabus detail (`/syllabuses/[slug]`) — tab group:
  - **Overview tab** — organisation text, focus-area accordions (K–2, 3–6, 7–10), contextual sections (Access content points, Life Skills, Protocols, Balance of content, Working at different stages, etc.)
  - **Aim and rationale tab** — aim statement + full rationale text
  - **Outcomes tab** — all outcomes per stage, grouped by focus area, with outcome code badges
  - **Content tab** — focus areas as collapsible panels; content groups + items with examples; glossary term links styled
  - **Assessment tab** — placeholder with link to live site
  - **Glossary tab** — placeholder with link to live site
  - Stage selector (`wa-select`) — sticky, filters Outcomes + Content tabs simultaneously
  - Zero-content syllabuses → "not yet available" state
- [x] Deployed to Cloudflare Pages via GitHub Actions

### 🔗 Phase 3 — ACARA Code Mapping

Map NSW outcome codes (e.g. `EN2-CWT-01`) to Australian Curriculum codes (e.g. `ACELA1545`).

#### 3a — DOCX extraction
- [ ] Resolve `link_resource_file` asset URLs from Kentico
- [ ] Download AC mapping Word documents (one per KLA/syllabus)
- [ ] Parse with `python-docx` → structured JSON in `data/ac-mapping/`

#### 3b — ACARA API
- [ ] Investigate ACARA API (australiancurriculum.edu.au, Version 9.0)
- [ ] Fetch AC content descriptions and codes by learning area + year level
- [ ] Cross-reference with NSW outcomes by stage/year taxonomy

#### 3c — Display integration
- [ ] Surface AC codes alongside NSW outcomes on site
- [ ] Link out to ACARA for each code
- [ ] Flag NSW-specific content with no AC equivalent

### 📄 Phase 4 — Missing syllabus content

- [ ] Fetch and display **Assessment** pages (same endpoint pattern: `/{slug}/assessment`)
- [ ] Fetch and display **Glossary** pages (same endpoint pattern: `/{slug}/glossary`)
- [ ] Resolve glossary term links in content items (currently `<a href="">` empty hrefs)
- [ ] Re-check the 11 zero-content Stage 6 syllabuses — NESA publishing is ongoing

### 🔍 Phase 5 — Discovery features

- [ ] **Outcomes cross-reference** — all Stage 3 outcomes across all KLAs on one page
- [ ] **Outcome code decoder** — paste a code like `EN3-CWT-01`, get the outcome + context
- [ ] **Syllabus timeline** — curriculum reform history visualised
- [ ] **Search** — Pagefind or Fuse.js over outcomes + content items

### ⚙️ Phase 6 — Automation

- [ ] Scheduled build-ID check (weekly cron via GitHub Actions)
- [ ] Auto-trigger content re-fetch on build-ID change
- [ ] Update `state.json` to track content fetch state per syllabus

---

## Data notes

### Syllabus list (source of truth)
`data/content/syllabuses.json` — derived from the live site. 88 syllabuses total:
- **69 with content** — full FA pages fetched and transformed
- **8 legacy CEC** — pre-2010 courses, no content in the new system (Ceramics, Computing Applications, Marine Studies, Photography/Video, Sport/Lifestyle, Visual Design, Work Studies, Numeracy, Exploring Early Childhood)
- **11 Stage 6 not yet published** — English Advanced, EAL/D, Maths Extension 1/2/Advanced, Economics, History Extension, Music 2, Music Extension, Software Engineering

### Focus-area structure
Each syllabus page on curriculum.nsw.edu.au routes to a stage → focus area URL:
```
/learning-areas/{kla}/{slug}/content/{stage-slug}/{fa-id}
```
The `defaultFocusAreaUrls` map in each overview JSON gives the entry point per stage. Each FA page's `stageFocusAreas` array lists all FAs for that stage group. Two-pass discovery: fetch defaults → discover additional FAs from the response.

### Kentico object resolution
Rich-text fields contain `<object type="application/kenticocloud" data-codename="...">` tags referencing linked items. The transformer resolves:
- `contentrichtext` → inline HTML
- `ui_media` → `<p class="fig-caption">caption</p>`  
- `ui_accordion` + `accordion_item` → native `<details>` elements

Unresolved refs are stripped cleanly (no broken markup in output).

---

## Open questions

- **Audience:** Teachers navigating outcomes? Students? Parents? Researchers?
- **ACARA scope:** Full mapping or just the published syllabuses?
- **Search depth:** Outcome-level or content-item level?
- **Document generation** (Phase 4 from original plan) — still relevant?
