#!/usr/bin/env python3
"""
Extract course enrolment details from raw content snapshots.
Outputs site/src/data/course-descriptions.json
"""

import json
import os
import sys

BASE = os.path.expanduser("~/code/curriculum-remix")
CONTENT_DIR = os.path.join(BASE, "data", "content")
OUTPUT = os.path.join(BASE, "site", "src", "data", "course-descriptions.json")

# Also load syllabuses.json for slug → curriculumUrl mapping
SYLLABUSES_JSON = os.path.join(BASE, "site", "src", "data", "syllabuses.json")

with open(SYLLABUSES_JSON) as f:
    syllabuses_list = json.load(f)

slug_to_meta = {s["slug"]: s for s in syllabuses_list}


def extract_tax(elements, key):
    """Extract taxonomy values as list of name strings."""
    return [v["name"] for v in elements.get(key, {}).get("value", [])]


def extract_text(elements, key):
    """Extract text field value."""
    return elements.get(key, {}).get("value", "")


def extract_mc(elements, key):
    """Extract multiple_choice codename."""
    vals = elements.get(key, {}).get("value", [])
    return vals[0]["codename"] if vals else None


all_courses = []
seen_course_ids = set()  # deduplicate across files for same syllabus

for syl_dir in sorted(os.listdir(CONTENT_DIR)):
    syl_path = os.path.join(CONTENT_DIR, syl_dir)
    if not os.path.isdir(syl_path):
        continue

    meta = slug_to_meta.get(syl_dir, {})
    found_courses = []

    # Walk all JSON files in this syllabus directory tree
    for root, dirs, files in os.walk(syl_path):
        for fn in sorted(files):
            if not fn.endswith(".json"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp) as f:
                    d = json.load(f)
            except Exception:
                continue

            courses = (
                d.get("pageProps", {})
                .get("data", {})
                .get("syllabusCourses", [])
            )

            for c in courses:
                e = c.get("elements", {})
                # Only include courses marked for display on course description page
                if extract_mc(e, "display_overview") != "yes":
                    continue

                course_id = extract_text(e, "courseid").strip()
                name = extract_text(e, "name").strip()

                # Deduplicate: same course can appear in multiple page files
                dedup_key = f"{syl_dir}::{course_id}::{name}"
                if dedup_key in seen_course_ids:
                    continue
                seen_course_ids.add(dedup_key)

                hours_list = extract_tax(e, "coursehours")
                hours = hours_list[0] if hours_list else ""

                units_list = extract_tax(e, "courseunits")
                units = units_list[0] if units_list else ""

                enrolment_list = extract_tax(e, "enrolmenttype")
                enrolment_type = ", ".join(enrolment_list)

                course_type_list = extract_tax(e, "coursetype")
                course_type = ", ".join(course_type_list)

                endorsement_list = extract_tax(e, "endorsementtype")
                endorsement_type = ", ".join(endorsement_list)

                stages = extract_tax(e, "stages")
                stage_years = extract_tax(e, "stage_years")

                kla_list = extract_tax(e, "key_learning_area_taxo")
                kla_label = kla_list[0] if kla_list else meta.get("klaLabel", "")
                kla = (
                    meta.get("kla", kla_label.lower().replace(" ", "-"))
                    if meta
                    else kla_label.lower().replace(" ", "-")
                )

                syllabus_names = extract_tax(e, "syllabus_taxo")
                syllabus_name = syllabus_names[0] if syllabus_names else meta.get("name", syl_dir)

                found_courses.append(
                    {
                        "syllabusSlug": syl_dir,
                        "syllabusName": syllabus_name,
                        "syllabusUrl": f"/syllabuses/{syl_dir}",
                        "kla": kla,
                        "klaLabel": kla_label,
                        "stages": stages,
                        "stageYears": stage_years,
                        "name": name,
                        "courseId": course_id,
                        "hours": hours,
                        "units": units,
                        "enrolmentType": enrolment_type,
                        "courseType": course_type,
                        "endorsementType": endorsement_type,
                    }
                )

    all_courses.extend(found_courses)

# Sort: KLA, then syllabus name, then course name
all_courses.sort(key=lambda c: (c["kla"], c["syllabusName"], c["name"]))

with open(OUTPUT, "w") as f:
    json.dump(all_courses, f, indent=2, ensure_ascii=False)

print(f"Wrote {len(all_courses)} courses to {OUTPUT}")
