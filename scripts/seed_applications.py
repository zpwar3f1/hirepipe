"""Write 5 mock Jotform applications covering all decision paths."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP_DIR = ROOT / "data" / "applications"
APP_DIR.mkdir(parents=True, exist_ok=True)


def _build(submission_id, first, last, role, answers):
    return {
        "submission_id": submission_id,
        "submitted_at": "2026-05-22T09:00:00",
        "first_name": first,
        "last_name": last,
        "email": f"{first.lower()}.{last.lower()}@example.com",
        "phone": "+15555550100",
        "role_applying_for": role,
        "license_photo_path": f"data/applications/{submission_id}_license.jpg",
        "answers": answers,
    }


APPS = [
    # 1. Strong driver — clears knockouts, all scores >= 8 -> request insurance
    _build("jf_001", "Marcus", "Johnson", "driver", {
        "saturdays": "yes",
        "drug_screen": "yes",
        "transportation": "yes",
        "age": "32",
        "license_valid": "yes",
        "years_experience": "8 years of professional driving and moving experience, both local and long-haul",
        "can_lift_75lbs": "yes",
        "state": "TX",
        "why_us": "I've worked with two other moving companies in Austin and want to work somewhere with better insurance and equipment.",
    }),
    # 2. Strong mover — clears, all scores >= 8 -> ready_to_interview (no insurance)
    _build("jf_002", "Aisha", "Patel", "mover", {
        "saturdays": "yes",
        "drug_screen": "yes",
        "transportation": "yes",
        "age": "26",
        "years_experience": "3 years on a moving crew plus warehouse work before that",
        "can_lift_75lbs": "yes",
        "state": "TX",
        "why_us": "I want consistent hours and a team that takes care of equipment. The reviews suggested FCM does both.",
    }),
    # 3. Knockout fail — can't work Saturdays
    _build("jf_003", "Jordan", "Lee", "driver", {
        "saturdays": "no",
        "drug_screen": "yes",
        "transportation": "yes",
        "age": "29",
        "license_valid": "yes",
        "years_experience": "5 years",
        "can_lift_75lbs": "yes",
        "state": "TX",
        "why_us": "Looking for steady weekday work",
    }),
    # 4. Score fail — low physical capability + low availability
    _build("jf_004", "Pat", "Nguyen", "mover", {
        "saturdays": "no",
        "drug_screen": "yes",
        "transportation": "yes",
        "age": "24",
        "years_experience": "1 year, mostly retail",
        "can_lift_75lbs": "no",
        "state": "TX",
        "why_us": "Looking for a change",
    }),
    # 5. Strong driver — for the insurance-loop / nudges demo
    _build("jf_005", "Diane", "Carter", "driver", {
        "saturdays": "yes",
        "drug_screen": "yes",
        "transportation": "yes",
        "age": "35",
        "license_valid": "yes",
        "years_experience": "12 years driving, 4 years at a moving company in Houston",
        "can_lift_75lbs": "yes",
        "state": "TX",
        "why_us": "Relocating to Austin and looking for a longer-term position with a team I respect.",
    }),
]

for app in APPS:
    (APP_DIR / f"{app['submission_id']}.json").write_text(
        json.dumps(app, indent=2), encoding="utf-8")

print(f"Wrote {len(APPS)} mock applications to {APP_DIR}")
