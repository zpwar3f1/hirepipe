"""Score evaluation + decision routing."""
from __future__ import annotations

import json
from pathlib import Path

from models import Decision, Role, ScoredApplication


def load_threshold(config_path: Path) -> dict:
    return json.loads(config_path.read_text(encoding="utf-8"))


def route(app: ScoredApplication, threshold_config: dict) -> tuple[Decision, str]:
    """Decide what to do with a fully scored application."""
    # Knockouts win first.
    if app.knockout_failures:
        return Decision.REJECT_KNOCKOUT, (
            "Knockout failure(s): " + ", ".join(app.knockout_failures)
        )

    if not app.scores:
        return Decision.REJECT_SCORE, "No scores produced"

    min_score = threshold_config["min_score_per_axis"]
    axes = threshold_config["axes"]
    scores_dict = app.scores.model_dump()
    failing_axes = [a for a in axes if scores_dict.get(a, 0) < min_score]
    if failing_axes:
        return Decision.REJECT_SCORE, (
            f"Score(s) below {min_score}: " + ", ".join(
                f"{a}={scores_dict[a]}" for a in failing_axes)
        )

    if app.submission.role_applying_for == Role.DRIVER:
        return Decision.REQUEST_INSURANCE, "All scores passed; driver requires insurance check"
    return Decision.READY_TO_INTERVIEW, "All scores passed; non-driver role"
