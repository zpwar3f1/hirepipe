"""Knockout question evaluation."""
from __future__ import annotations

import json
from pathlib import Path

from models import JotformSubmission


def load_knockouts(config_path: Path) -> list[dict]:
    return json.loads(config_path.read_text(encoding="utf-8"))["knockouts"]


def evaluate(submission: JotformSubmission, knockouts: list[dict]) -> list[str]:
    """Return a list of knockout IDs the applicant failed."""
    answers_lower = {k.lower(): (v or "").strip().lower() for k, v in submission.answers.items()}
    role = submission.role_applying_for.value
    failed: list[str] = []

    for ko in knockouts:
        role_scoped = ko.get("role_specific")
        if role_scoped and role not in role_scoped:
            continue
        ko_id = ko["id"]
        ans = answers_lower.get(ko_id, "")
        if ans in [s.lower() for s in ko["fail_on"]]:
            failed.append(ko_id)
        # Missing answers count as failures for safety.
        if not ans:
            failed.append(f"{ko_id}_missing")

    return failed
