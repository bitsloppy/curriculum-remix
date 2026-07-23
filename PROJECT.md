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

### 📄 Phase 4 — Document Assembly

Generate formatted Word/PDF curriculum documents from the structured data.

**Content hierarchy available:**
```
Syllabus → Course → Focus Area → Outcome(s)
                               → Content Groups → Content Items (dot-point content)
```

- [ ] Fetch all stage/focus-area content pages (~175 pages across all syllabuses)
- [ ] Reconstruct full document hierarchy from JSON
- [ ] DOCX output via `python-docx`
- [ ] PDF output via `mdtopdf` pipeline

**Possible document types:**
- Full syllabus reprint (outcomes + content, formatted)
- Scope and sequence table (outcomes × stages)
- Year level snapshot (all content for Year 5 across all KLAs)
- Teacher unit planning template (pre-filled with outcomes + content points)
- AC mapping overlay (NSW outcomes → ACARA codes side by side)

### ⚙️ Phase 5 — Automation
- [ ] Scheduled check for new NESA builds (weekly cron)
- [ ] Auto-commit snapshots on build change
- [ ] Trigger site rebuild on new data

---

## Open Questions

### Audience & scope
- **Who is the primary audience?** Teachers? Students? Parents? Researchers?
- **What's the core use case?** Browse/discover? Generate documents? Cross-reference? Research?
- **Static or interactive?** Fully static (fast, cheap) or search/filter (needs JS or a backend)?

### Data depth
- **Go deeper into individual syllabus pages?** Content-point level data exists at `/learning-areas/<kla>/<syllabus>/content/<stage>/` — 175 pages available, much richer but a bigger fetch.
- **Include teaching advice?** Present at stage level, optional not mandatory.
- **Include glossary terms?** Inline in content items as linked terms.
