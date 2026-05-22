"""Tests for knockout evaluation."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from knockouts import evaluate, load_knockouts  # noqa: E402
from models import JotformSubmission, Role  # noqa: E402


KOS = load_knockouts(ROOT / "config" / "knockout_questions.json")


def _submission(role: Role, **answers) -> JotformSubmission:
    return JotformSubmission(
        submission_id="x",
        submitted_at=datetime.now(),
        first_name="A",
        last_name="B",
        email="a@b.com",
        phone="555",
        role_applying_for=role,
        answers=answers,
    )


def test_passing_driver_has_no_failures():
    sub = _submission(
        Role.DRIVER,
        saturdays="yes", drug_screen="yes", transportation="yes",
        age="25", license_valid="yes",
    )
    assert evaluate(sub, KOS) == []


def test_saturday_no_fails():
    sub = _submission(
        Role.DRIVER,
        saturdays="no", drug_screen="yes", transportation="yes",
        age="25", license_valid="yes",
    )
    fails = evaluate(sub, KOS)
    assert "saturdays" in fails


def test_license_question_skipped_for_mover():
    sub = _submission(
        Role.MOVER,
        saturdays="yes", drug_screen="yes", transportation="yes",
        age="25",
        # no license_valid answer -- should NOT count as failure for mover
    )
    fails = evaluate(sub, KOS)
    assert "license_valid" not in fails
    assert "license_valid_missing" not in fails


def test_missing_answer_counts_as_failure():
    sub = _submission(
        Role.DRIVER,
        saturdays="yes", drug_screen="yes", transportation="yes",
        # missing age, license_valid
    )
    fails = evaluate(sub, KOS)
    assert "age_missing" in fails
    assert "license_valid_missing" in fails
