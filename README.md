# curriculum-remix

A project that pulls structured curriculum data from the NSW Education Standards Authority (NESA) and uses it as the foundation for a display website.

## How the data works

[curriculum.nsw.edu.au](https://curriculum.nsw.edu.au) is a Next.js app backed by a Kentico Kontent CMS. Every page has a pre-rendered JSON file available at:

```
https://curriculum.nsw.edu.au/_next/data/<build-id>/<slug>.json
```

The build ID changes with each deployment. The fetch script detects this automatically.

## Fetching data

```bash
# Only fetches if the site has deployed a new build
python3 scripts/fetch-data.py

# Force re-fetch even if build ID hasn't changed
python3 scripts/fetch-data.py --force
```

Snapshots are saved to `data/snapshots/<timestamp>_<build-id>/`.  
Current build state is tracked in `data/state.json`.

## Project structure

```
curriculum-remix/
├── scripts/
│   └── fetch-data.py     # Data fetcher
├── data/
│   ├── state.json        # Tracks current build ID + last fetch time
│   └── snapshots/        # Versioned data snapshots
│       └── YYYY-MM-DD_HHmmss_<build-id>/
│           ├── learning-areas.json
│           ├── english.json
│           ├── mathematics.json
│           └── ...
└── site/                 # Display website (TBD)
```

## Data format

Each JSON file contains a Next.js `pageProps` object with Kentico Kontent content items. Each item has:

- **`system`** — codename, id, type, lastModified
- **`elements`** — typed fields: text, rich_text, taxonomy (KLA, stage, year), modular_content, url_slug, assets

Key taxonomy fields to filter by:
- `key_learning_area__items` — English, Mathematics, Science, TAS, HSIE, Creative Arts, PDHPE, Languages, VET
- `stages__stages` — Early Stage 1 through Stage 6
- `stages__stage_years` — K, 1–12

## Pages fetched

| Slug | Content |
|---|---|
| `learning-areas` | All KLA overview + nav |
| `learning-areas/english` | English syllabuses |
| `learning-areas/mathematics` | Mathematics syllabuses |
| `learning-areas/science` | Science syllabuses |
| `learning-areas/tas` | TAS syllabuses |
| `learning-areas/hsie` | HSIE syllabuses |
| `learning-areas/creative-arts` | Creative Arts syllabuses |
| `learning-areas/pdhpe` | PDHPE syllabuses |
| `learning-areas/languages` | Languages syllabuses |
| `learning-areas/vet` | VET syllabuses |
