"""Scenario 4: Calendly booking watcher — schedule reminders."""
from __future__ import annotations

from datetime import datetime, timedelta

from models import ReminderEntry


REMINDER_CADENCE = [
    # (offset_before_interview, cadence_label, channels)
    (timedelta(hours=48),   "48h",   ["email", "sms"]),
    (timedelta(hours=24),   "24h",   ["email", "sms"]),
    (timedelta(hours=2),    "2h",    ["sms"]),
    (timedelta(minutes=30), "30min", ["sms"]),
]


def build_reminder_schedule(*,
                              candidate_id: str,
                              candidate_first_name: str,
                              candidate_email: str,
                              candidate_phone: str,
                              interview_at: datetime,
                              now: datetime) -> list[ReminderEntry]:
    """Return all reminders to schedule. Skips any in the past."""
    out: list[ReminderEntry] = []
    for offset, cadence, channels in REMINDER_CADENCE:
        fires_at = interview_at - offset
        if fires_at <= now:
            continue
        out.append(ReminderEntry(
            candidate_id=candidate_id,
            candidate_first_name=candidate_first_name,
            candidate_phone=candidate_phone,
            candidate_email=candidate_email,
            interview_at=interview_at,
            fires_at=fires_at,
            cadence=cadence,
            channel=channels,
        ))
    return out
