#!/usr/bin/env python3
"""Parse NESA syllabus CSV into site-ready JSON."""

import csv, json, re, sys
from pathlib import Path

CSV_PATH = Path(__file__).parent.parent / 'data' / 'syllabuses-raw.csv'
OUT_PATH = Path(__file__).parent.parent / 'site' / 'src' / 'data' / 'syllabuses.json'

KLA_MAP = {
    'ART':   'creative-arts',
    'ENG':   'english',
    'HSIE':  'hsie',
    'LANG':  'languages',
    'MATHS': 'mathematics',
    'PDHPE': 'pdhpe',
    'SCI':   'science',
    'TAS':   'tas',
}

KLA_LABELS = {
    'creative-arts': 'Creative Arts',
    'english':       'English',
    'hsie':          'Human Society and its Environment',
    'languages':     'Languages',
    'mathematics':   'Mathematics',
    'pdhpe':         'PDHPE',
    'science':       'Science',
    'tas':           'Technological and Applied Studies',
}

def slugify(code: str) -> str:
    """ENGLISH-K–10-2022 → english-k-10-2022"""
    s = code.lower()
    s = s.replace('–', '-').replace('—', '-')   # en/em dashes
    s = re.sub(r'[^a-z0-9-]', '-', s)
    s = re.sub(r'-+', '-', s).strip('-')
    return s

def clean(val: str) -> str:
    return val.strip()

def nullish(val: str):
    v = clean(val)
    return None if v in ('', '--', 'NA', '??') else v

syllabuses = []

with open(CSV_PATH, newline='', encoding='utf-8-sig') as f:
    reader = csv.reader(f)
    headers = next(reader)

    for row in reader:
        if len(row) < 13:
            continue
        # Pad row to avoid index errors
        row = row + [''] * 24

        id_      = clean(row[0])
        published= clean(row[1]) == 'YES'
        type_    = clean(row[2])      # MS or LS
        classif  = nullish(row[3])    # MANDATORY / ELECTIVE (5) / MANDALECTIVES / None
        kla_raw  = clean(row[4])
        stage    = clean(row[5])
        name     = clean(row[6])
        pages    = nullish(row[7])
        old_url  = nullish(row[8])
        new_url  = nullish(row[9])
        code     = nullish(row[10])
        pub_year = nullish(row[11])
        syl_code = nullish(row[12])

        if not id_ or not name:
            continue

        kla_slug  = KLA_MAP.get(kla_raw)
        kla_label = KLA_LABELS.get(kla_slug, kla_raw) if kla_slug else kla_raw

        slug = slugify(syl_code) if syl_code else slugify(name)

        # Parse pages to int if possible
        try:
            pages = int(pages) if pages else None
        except (ValueError, TypeError):
            pages = None

        # Classification
        is_mandatory = False
        is_elective  = False
        elective_periods = None
        if classif:
            cl = classif.upper()
            if 'MANDATORY' in cl:
                is_mandatory = True
            if 'ELECTIVE' in cl:
                is_elective = True
                m = re.search(r'\((\d+)\)', classif)
                if m:
                    elective_periods = int(m.group(1))
            if 'MANDALECTIVES' in cl:
                is_mandatory = True
                is_elective  = True

        syllabuses.append({
            'id':               id_,
            'slug':             slug,
            'name':             name,
            'kla':              kla_slug,
            'klaLabel':         kla_label,
            'stage':            stage,
            'type':             type_,        # MS or LS
            'published':        published,    # on curriculum.nsw.edu.au
            'isMandatory':      is_mandatory,
            'isElective':       is_elective,
            'electivePeriods':  elective_periods,
            'pages':            pages,
            'nesaUrl':          old_url,
            'curriculumUrl':    new_url,
            'code':             code,
            'pubYear':          pub_year,
            'syllabusCode':     syl_code,
        })

OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUT_PATH, 'w', encoding='utf-8') as f:
    json.dump(syllabuses, f, indent=2, ensure_ascii=False)

print(f'Written {len(syllabuses)} syllabuses → {OUT_PATH}')
