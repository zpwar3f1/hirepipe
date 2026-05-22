"""Scenario 1 orchestrator: Jotform -> Claude -> route -> notify."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from knockouts import evaluate, load_knockouts
from license_scorer import Scorer, get_scorer
from models import (
    Decision,
    JotformSubmission,
    PendingInsuranceEntry,
    Role,
    ScoredApplication,
)
from routing import load_threshold, route
from state_store import PendingInsuranceStore


def _render_template(template_path: Path, vars: dict[str, str]) -> str:
    text = template_path.read_text(encoding="utf-8")
    for k, v in vars.items():
        text = text.replace("{{" + k + "}}", str(v))
    return text


def process_application(*,
                          submission: JotformSubmission,
                          scorer: Scorer,
                          prompt: str,
                          knockouts: list[dict],
                          threshold_config: dict,
                          email_dir: Path,
                          output_dir: Path,
                          state_store: PendingInsuranceStore,
                          insurance_agent: dict,
                          owner_email: str) -> ScoredApplication:
    """Run a single applicant through the full pipeline."""
    # 1. Knockouts (cheapest check first)
    failed_kos = evaluate(submission, knockouts)

    # 2. License + scores (skip Claude call if knockouts already disqualify? Brief says
    #    Claude is called either way for documentation — we honour that.)
    license, scores, rationale, concerns = scorer.score(submission, prompt=prompt)

    app = ScoredApplication(
        submission=submission,
        license=license,
        scores=scores,
        score_rationale=rationale,
        concerns=concerns,
        knockout_failures=failed_kos,
    )

    # 3. Routing
    decision, reason = route(app, threshold_config)
    app.decision = decision
    app.decision_reason = reason

    # 4. Side effects per decision
    candidate_dir = output_dir / submission.submission_id
    candidate_dir.mkdir(parents=True, exist_ok=True)

    if decision in (Decision.REJECT_KNOCKOUT, Decision.REJECT_SCORE):
        body = _render_template(email_dir / "rejection.md", {
            "candidate_first_name": submission.first_name,
            "role": submission.role_applying_for.value,
        })
        (candidate_dir / "gmail_rejection.txt").write_text(body, encoding="utf-8")

    elif decision == Decision.REQUEST_INSURANCE:
        # Send screening email to candidate
        candidate_body = _render_template(email_dir / "screening.md", {
            "candidate_first_name": submission.first_name,
            "role": submission.role_applying_for.value,
        })
        (candidate_dir / "gmail_screening.txt").write_text(candidate_body, encoding="utf-8")

        # Send insurance request to agent
        agent_body = _render_template(email_dir / "insurance_request.md", {
            "insurance_agent_name": insurance_agent["name"],
            "candidate_full_name": f"{submission.first_name} {submission.last_name}",
            "candidate_dob": license.dob.isoformat(),
            "license_number": license.license_number,
            "license_state": license.state,
            "license_class": license.class_,
            "license_expiration": license.expiration_date.isoformat(),
            "owner_email": owner_email,
        })
        (candidate_dir / "gmail_insurance_request.txt").write_text(agent_body, encoding="utf-8")

        # Add to PendingInsurance data store
        state_store.add(PendingInsuranceEntry(
            candidate_id=submission.submission_id,
            candidate_email=submission.email,
            candidate_first_name=submission.first_name,
            candidate_full_name=f"{submission.first_name} {submission.last_name}",
            license_number=license.license_number,
            role=submission.role_applying_for,
            requested_at=datetime.now(),
        ))

    elif decision == Decision.READY_TO_INTERVIEW:
        body = _render_template(email_dir / "congrats_calendly.md", {
            "candidate_first_name": submission.first_name,
            "calendly_link": "https://calendly.com/fcm/interview",
        })
        (candidate_dir / "gmail_congrats.txt").write_text(body, encoding="utf-8")

    # 5. Audit artifacts
    (candidate_dir / "decision.json").write_text(
        json.dumps({
            "submission_id": submission.submission_id,
            "candidate": f"{submission.first_name} {submission.last_name}",
            "role": submission.role_applying_for.value,
            "decision": decision.value,
            "decision_reason": reason,
            "knockout_failures": failed_kos,
            "scores": scores.model_dump(),
            "concerns": concerns,
            "license_summary": {
                "number": license.license_number,
                "state": license.state,
                "class": license.class_,
                "expires": license.expiration_date.isoformat(),
                "confidence": license.extraction_confidence,
            },
        }, indent=2), encoding="utf-8")

    return app
