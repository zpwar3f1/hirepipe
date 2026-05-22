"""Tests for the reminder scheduler."""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from reminders import build_reminder_schedule  # noqa: E402


def test_full_schedule_when_booked_in_advance():
    interview = datetime(2026, 6, 1, 14, 0)
    now = datetime(2026, 5, 27, 10, 0)
    sched = build_reminder_schedule(
        candidate_id="c1",
        candidate_first_name="Test",
        candidate_email="t@e.com",
        candidate_phone="+1",
        interview_at=interview,
        now=now,
    )
    cadences = [r.cadence for r in sched]
    assert cadences == ["48h", "24h", "2h", "30min"]
    # Fires_at values are computed correctly
    by = {r.cadence: r.fires_at for r in sched}
    assert by["48h"] == datetime(2026, 5, 30, 14, 0)
    assert by["24h"] == datetime(2026, 5, 31, 14, 0)
    assert by["2h"]  == datetime(2026, 6, 1, 12, 0)
    assert by["30min"] == datetime(2026, 6, 1, 13, 30)


def test_late_booking_skips_past_reminders():
    interview = datetime(2026, 6, 1, 14, 0)
    now = datetime(2026, 5, 31, 18, 0)  # ~20h before — 48h already past
    sched = build_reminder_schedule(
        candidate_id="c1",
        candidate_first_name="Test",
        candidate_email="t@e.com",
        candidate_phone="+1",
        interview_at=interview,
        now=now,
    )
    cadences = [r.cadence for r in sched]
    # 48h fires_at was 2 days before interview = 2026-05-30 14:00, before now -> skipped
    assert "48h" not in cadences
    assert "24h" not in cadences   # 24h reminder fires_at = 5/31 14:00, also before now
    assert "2h" in cadences
    assert "30min" in cadences


def test_no_reminders_when_interview_imminent():
    interview = datetime(2026, 6, 1, 14, 0)
    now = datetime(2026, 6, 1, 13, 45)  # 15 min before
    sched = build_reminder_schedule(
        candidate_id="c1",
        candidate_first_name="Test",
        candidate_email="t@e.com",
        candidate_phone="+1",
        interview_at=interview,
        now=now,
    )
    assert sched == []
