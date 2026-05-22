"""Claude vision wrapper for license OCR + applicant scoring.

`MockScorer` returns deterministic plausible outputs based on the
applicant's submission metadata so the pipeline runs offline.
`ClaudeScorer` calls the real vision API.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Optional, Protocol

from models import JotformSubmission, LicenseFields, Scores


class Scorer(Protocol):
    def score(self, submission: JotformSubmission, *, prompt: str
                ) -> tuple[LicenseFields, Scores, dict[str, str], list[str]]: ...


class MockScorer:
    """Deterministic mock for offline testing.

    Pulls answers from the submission to drive a realistic-looking result.
    """

    def score(self, submission: JotformSubmission, *, prompt: str = ""
                ) -> tuple[LicenseFields, Scores, dict[str, str], list[str]]:
        ans = {k.lower(): v.strip().lower() for k, v in submission.answers.items()}

        # Mock license: derive a fake-but-shaped license number from the email.
        license_num = re.sub(r"[^A-Z0-9]", "", submission.email.upper())[:9].ljust(9, "0")
        # Pull years of experience from the answers if present.
        yoe = 0
        m = re.search(r"(\d+)", ans.get("years_experience", "") or "0")
        if m:
            yoe = int(m.group(1))

        # Pretend the license is valid for the next year.
        today = date(2026, 5, 22)
        license = LicenseFields(
            license_number=license_num,
            full_name=f"{submission.first_name} {submission.last_name}",
            dob=date(today.year - max(21, _guess_age(ans)), 1, 1),
            expiration_date=today + timedelta(days=365 + yoe % 60),
            state=ans.get("state", "TX")[:2].upper() or "TX",
            **{"class": "C" if submission.role_applying_for.value == "driver" else "NONE"},
            endorsements=[],
            restrictions=[r for r in (ans.get("restrictions", "") or "").split(",") if r],
            extraction_confidence=0.92,
        )

        # Scoring heuristics from the form answers. Tuned so applicants who
        # answer "yes" to the knockouts AND have at least 2 years experience
        # AND write meaningful long-form answers cleanly clear the >=8
        # threshold; the harshness lives in the knockout step.
        if yoe == 0:
            experience = 3
        elif yoe == 1:
            experience = 6
        elif yoe <= 3:
            experience = 8
        elif yoe <= 6:
            experience = 9
        else:
            experience = 10
        availability = 10 if ans.get("saturdays") in ("yes", "y", "true") else 4
        long_form_text = ans.get("why_us", "") + " " + ans.get("years_experience", "")
        if len(long_form_text) > 120:
            professionalism = 9
        elif len(long_form_text) > 50:
            professionalism = 8
        else:
            professionalism = 4
        physical = 9 if ans.get("can_lift_75lbs") in ("yes", "y", "true") else 3

        scores = Scores(
            experience=experience,
            availability=availability,
            professionalism=professionalism,
            physical_capability=physical,
        )
        rationale = {
            "experience": f"{yoe} year(s) of stated relevant experience",
            "availability": "Saturday availability confirmed" if availability >= 8 else "Saturday availability uncertain",
            "professionalism": f"{len(long_form_text)} chars of long-form answer detail",
            "physical_capability": "Confirmed able to lift 75lbs" if physical >= 8 else "Did not confirm physical readiness",
        }

        concerns = []
        if license.expiration_date <= today + timedelta(days=60):
            concerns.append("license expires within 60 days")
        if license.full_name.lower() != f"{submission.first_name.lower()} {submission.last_name.lower()}":
            concerns.append("name on license does not match form")
        if yoe == 0:
            concerns.append("zero years of stated experience")

        return license, scores, rationale, concerns


def _guess_age(ans: dict[str, str]) -> int:
    m = re.search(r"(\d+)", ans.get("age", "") or "0")
    return int(m.group(1)) if m else 21


class ClaudeScorer:  # pragma: no cover — live only
    """Real Claude vision-backed scorer.

    Expects the license image to be at `submission.license_photo_path`.
    Loads it, base64-encodes it, sends it to the vision model along
    with the system prompt + applicant answers.
    """

    def __init__(self, *, api_key: Optional[str] = None,
                  model: str = "claude-sonnet-4-6"):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.model = model
        self._client = None

    def _client_or_raise(self):
        if self._client is not None:
            return self._client
        try:
            import anthropic  # type: ignore
        except ImportError as e:
            raise RuntimeError("pip install anthropic") from e
        if not self.api_key:
            raise RuntimeError("ANTHROPIC_API_KEY required for live ClaudeScorer")
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client

    def score(self, submission: JotformSubmission, *, prompt: str
                ) -> tuple[LicenseFields, Scores, dict[str, str], list[str]]:
        client = self._client_or_raise()
        import base64
        img_path = Path(submission.license_photo_path)
        if not img_path.exists():
            raise RuntimeError(f"License image not found: {img_path}")
        img_b64 = base64.standard_b64encode(img_path.read_bytes()).decode("ascii")

        user_message = (
            f"Application answers:\n"
            + "\n".join(f"  {k}: {v}" for k, v in submission.answers.items())
            + f"\n\nRole: {submission.role_applying_for.value}"
        )

        resp = client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=prompt,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64",
                                                    "media_type": "image/jpeg",
                                                    "data": img_b64}},
                    {"type": "text", "text": user_message},
                ],
            }],
        )
        raw = json.loads(resp.content[0].text)  # type: ignore[index]
        return (
            LicenseFields(**raw["license"]),
            Scores(**raw["scores"]),
            raw.get("score_rationale", {}),
            raw.get("concerns", []),
        )


def get_scorer() -> Scorer:
    if os.environ.get("LLM_MODE", "").lower() == "live":
        return ClaudeScorer()
    return MockScorer()
