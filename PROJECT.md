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

### 🔗 Phase 2 — ACARA Code Mapping

Map NSW outcome codes (e.g. `EN2-CWT-01`) to Australian Curriculum codes (e.g. `ACELA1545`).

#### 2a — DOCX extraction
- [ ] Resolve `link_resource_file` asset URLs from Kentico
- [ ] Download AC mapping Word documents (one per KLA/syllabus)
- [ ] Parse with `python-docx` → structured JSON in `data/ac-mapping/`

#### 2b — ACARA API
- [ ] Investigate ACARA API (australiancurriculum.edu.au, Version 9.0)
- [ ] Fetch AC content descriptions and codes by learning area + year level
- [ ] Cross-reference with NSW outcomes by stage/year taxonomy

#### 2c — Display integration
- [ ] Surface AC codes alongside NSW outcomes on site
- [ ] Link out to ACARA for each code
- [ ] Flag NSW-specific content with no AC equivalent

### 🌐 Phase 3 — Display Website

#### Core views
- [ ] Home — all 9 KLAs with stage/year navigation
- [ ] Browse by KLA — syllabus list per learning area
- [ ] Browse by stage/year — everything for a given year level across all KLAs
- [ ] Cross-KLA by stage — side-by-side view across subjects
- [ ] Syllabus detail — outcomes by strand, with AC codes
- [ ] Outcome detail — single outcome with context and AC mapping

#### Discovery features
- [ ] Outcome code explorer — decode NSW code structure
- [ ] Syllabus timeline — curriculum reform history visualised
- [ ] Capabilities/priorities overlay — cross-curriculum priority tagging

#### Technical
- [ ] Framework choice (Astro likely)
- [ ] Data transformation layer (Kentico JSON → site-ready format)
- [ ] Static build from snapshot data
- [ ] Deploy to Cloudflare Pages
- [ ] GitHub Actions CI/CD

### ⚙️ Phase 4 — Automation
- [ ] Scheduled check for new NESA builds (weekly cron)
- [ ] Auto-commit snapshots on build change
- [ ] Trigger site rebuild on new data

---

## Open Questions

- What's the primary audience? (Teachers / students / parents / researchers?)
- Static or interactive (search/filter)?
- Go deeper into individual syllabus pages for content-point level data?
