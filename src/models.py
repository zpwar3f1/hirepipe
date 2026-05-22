"""Domain models for the hiring pipeline."""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Role(str, Enum):
    DRIVER = "driver"
    MOVER = "mover"


class Decision(str, Enum):
    REJECT_KNOCKOUT = "reject_knockout"
    REJECT_SCORE = "reject_score"
    REQUEST_INSURANCE = "request_insurance"
    READY_TO_INTERVIEW = "ready_to_interview"   # mover path skips insurance


class JotformSubmission(BaseModel):
    """What Jotform sends via webhook."""
    submission_id: str
    submitted_at: datetime
    first_name: str
    last_name: str
    email: str
    phone: str
    role_applying_for: Role
    license_photo_path: str = ""   # local path stand-in for the image URL
    answers: dict[str, str] = Field(default_factory=dict)


class LicenseFields(BaseModel):
    license_number: str
    full_name: str
    dob: date
    expiration_date: date
    state: str
    class_: str = Field(alias="class")
    endorsements: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    extraction_confidence: float = 0.0

    model_config = {"populate_by_name": True}


class Scores(BaseModel):
    experience: int
    availability: int
    professionalism: int
    physical_capability: int


class ScoredApplication(BaseModel):
    submission: JotformSubmission
    license: Optional[LicenseFields] = None
    scores: Optional[Scores] = None
    score_rationale: dict[str, str] = Field(default_factory=dict)
    concerns: list[str] = Field(default_factory=list)
    knockout_failures: list[str] = Field(default_factory=list)
    decision: Optional[Decision] = None
    decision_reason: str = ""


class PendingInsuranceEntry(BaseModel):
    candidate_id: str
    candidate_email: str
    candidate_first_name: str
    candidate_full_name: str
    license_number: str
    role: Role
    requested_at: datetime
    nudged_24h: bool = False
    nudged_48h: bool = False
    cleared_at: Optional[datetime] = None
    cleared_by: Optional[str] = None


class ReminderEntry(BaseModel):
    """One scheduled reminder for an upcoming interview."""
    candidate_id: str
    candidate_first_name: str
    candidate_phone: str
    candidate_email: str
    interview_at: datetime
    fires_at: datetime
    cadence: str    # "48h" / "24h" / "2h" / "30min"
    channel: list[str]   # ["email", "sms"] or ["sms"]
