"""Tests for score-based routing."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from models import Decision, JotformSubmission, Role, ScoredApplication, Scores  # noqa: E402
from routing import load_threshold, route  # noqa: E402


TH = load_threshold(ROOT / "config" / "scoring_threshold.json")


def _make(role: Role, *, scores: dict[str, int], kos: list[str] = ()) -> ScoredApplication:
    return ScoredApplication(
        submission=JotformSubmission(
            submission_id="x",
            submitted_at=datetime.now(),
            first_name="A", last_name="B",
            email="a@b.com", phone="5",
            role_applying_for=role,
        ),
        scores=Scores(**scores),
        knockout_failures=list(kos),
    )


def test_knockout_fail_short_circuits():
    app = _make(Role.DRIVER,
                 scores={"experience": 10, "availability": 10,
                         "professionalism": 10, "physical_capability": 10},
                 kos=["saturdays"])
    decision, reason = route(app, TH)
    assert decision == Decision.REJECT_KNOCKOUT


def test_driver_passing_goes_to_insurance():
    app = _make(Role.DRIVER,
                 scores={"experience": 9, "availability": 9,
                         "professionalism": 8, "physical_capability": 9})
    decision, _ = route(app, TH)
    assert decision == Decision.REQUEST_INSURANCE


def test_mover_passing_skips_insurance():
    app = _make(Role.MOVER,
                 scores={"experience": 9, "availability": 9,
                         "professionalism": 8, "physical_capability": 9})
    decision, _ = route(app, TH)
    assert decision == Decision.READY_TO_INTERVIEW


def test_low_score_rejects():
    app = _make(Role.DRIVER,
                 scores={"experience": 9, "availability": 9,
                         "professionalism": 7, "physical_capability": 9})
    decision, reason = route(app, TH)
    assert decision == Decision.REJECT_SCORE
    assert "professionalism" in reason
