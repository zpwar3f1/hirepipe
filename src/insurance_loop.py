"""Scenarios 2 + 3: insurance clearance loop + nudges."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from models import PendingInsuranceEntry
from state_store import PendingInsuranceStore


def _render(template_path: Path, vars: dict) -> str:
    text = template_path.read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def clear_candidate(*,
                      store: PendingInsuranceStore,
                      candidate_id: str,
                      cleared_by: str,
                      now: datetime,
                      output_dir: Path,
                      email_dir: Path,
                      calendly_link: str) -> PendingInsuranceEntry:
    """Scenario 2 — owner submits the private 'clear this candidate' Jotform."""
    entry = store.get(candidate_id)
    if entry is None:
        raise ValueError(f"Unknown candidate: {candidate_id}")
    store.clear(candidate_id, by=cleared_by, cleared_at=now)

    candidate_dir = output_dir / candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    body = _render(email_dir / "congrats_calendly.md", {
        "candidate_first_name": entry.candidate_first_name,
        "calendly_link": calendly_link,
    })
    (candidate_dir / "gmail_congrats.txt").write_text(body, encoding="utf-8")
    updated = store.get(candidate_id)
    assert updated is not None
    return updated


def run_nudges(*,
                 store: PendingInsuranceStore,
                 now: datetime,
                 output_dir: Path,
                 email_dir: Path,
                 owner_name: str,
                 owner_email: str,
                 insurance_agent_name: str) -> dict:
    """Scenario 3 — hourly job. Sends 24h candidate update + 48h escalation."""
    sent_24h: list[str] = []
    sent_48h: list[str] = []

    for entry in store.needing_24h_nudge(now=now):
        body = _render(email_dir / "nudge_24h.md", {
            "candidate_first_name": entry.candidate_first_name,
        })
        d = output_dir / entry.candidate_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "gmail_nudge_24h.txt").write_text(body, encoding="utf-8")
        store.mark_nudged(entry.candidate_id, level="24h")
        sent_24h.append(entry.candidate_id)

    for entry in store.needing_48h_nudge(now=now):
        candidate_body = _render(email_dir / "nudge_48h_candidate.md", {
            "candidate_first_name": entry.candidate_first_name,
        })
        owner_body = _render(email_dir / "nudge_48h_owner.md", {
            "owner_name": owner_name,
            "candidate_full_name": entry.candidate_full_name,
            "candidate_email": entry.candidate_email,
            "candidate_id": entry.candidate_id,
            "insurance_agent_name": insurance_agent_name,
            "pending_since": entry.requested_at.isoformat(timespec="minutes"),
        })
        d = output_dir / entry.candidate_id
        d.mkdir(parents=True, exist_ok=True)
        (d / "gmail_nudge_48h_candidate.txt").write_text(candidate_body, encoding="utf-8")
        (d / "gmail_nudge_48h_owner_escalation.txt").write_text(owner_body, encoding="utf-8")
        store.mark_nudged(entry.candidate_id, level="48h")
        sent_48h.append(entry.candidate_id)

    return {"nudged_24h": sent_24h, "nudged_48h": sent_48h}
