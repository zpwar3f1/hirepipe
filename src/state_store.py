"""JSON-backed PendingInsurance data store.

Mirrors what a Make data store does. Production wiring would swap this
for a Make-managed store accessed via its API or scenario modules; the
shape is the same.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from models import PendingInsuranceEntry


class PendingInsuranceStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, PendingInsuranceEntry] = self._load()

    def _load(self) -> dict[str, PendingInsuranceEntry]:
        if not self.path.exists():
            return {}
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        return {cid: PendingInsuranceEntry.model_validate(r) for cid, r in raw.items()}

    def _save(self) -> None:
        raw = {cid: r.model_dump(mode="json") for cid, r in self._records.items()}
        self.path.write_text(json.dumps(raw, indent=2, default=str), encoding="utf-8")

    def add(self, entry: PendingInsuranceEntry) -> None:
        self._records[entry.candidate_id] = entry
        self._save()

    def get(self, candidate_id: str) -> Optional[PendingInsuranceEntry]:
        return self._records.get(candidate_id)

    def mark_nudged(self, candidate_id: str, *, level: str) -> None:
        if candidate_id not in self._records:
            return
        if level == "24h":
            self._records[candidate_id].nudged_24h = True
        elif level == "48h":
            self._records[candidate_id].nudged_48h = True
        self._save()

    def clear(self, candidate_id: str, *, by: str,
                cleared_at: Optional[datetime] = None) -> None:
        if candidate_id not in self._records:
            return
        self._records[candidate_id].cleared_at = cleared_at or datetime.now()
        self._records[candidate_id].cleared_by = by
        self._save()

    def pending_only(self) -> list[PendingInsuranceEntry]:
        return [r for r in self._records.values() if r.cleared_at is None]

    def needing_24h_nudge(self, *, now: datetime) -> list[PendingInsuranceEntry]:
        cutoff = now - timedelta(hours=24)
        return [
            r for r in self.pending_only()
            if r.requested_at <= cutoff and not r.nudged_24h
        ]

    def needing_48h_nudge(self, *, now: datetime) -> list[PendingInsuranceEntry]:
        cutoff = now - timedelta(hours=48)
        return [
            r for r in self.pending_only()
            if r.requested_at <= cutoff and not r.nudged_48h
        ]
