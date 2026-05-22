"""End-to-end HirePipe demo.

Walks 5 mock applicants through all 4 scenarios:
  - Scenario 1: hiring pipeline (license OCR -> knockouts -> scores -> route)
  - Scenario 2: insurance loop (owner clears one candidate manually)
  - Scenario 3: nudges (fast-forward 24h and 48h to fire candidate / owner emails)
  - Scenario 4: Calendly booking watcher (build the reminder schedule)
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from insurance_loop import clear_candidate, run_nudges  # noqa: E402
from knockouts import load_knockouts  # noqa: E402
from license_scorer import MockScorer  # noqa: E402
from models import JotformSubmission, Role  # noqa: E402
from pipeline import process_application  # noqa: E402
from reminders import build_reminder_schedule  # noqa: E402
from routing import load_threshold  # noqa: E402
from state_store import PendingInsuranceStore  # noqa: E402


APP_DIR = ROOT / "data" / "applications"
OUT_DIR = ROOT / "data" / "output"
EMAIL_DIR = ROOT / "config" / "email_templates"
PROMPT_PATH = ROOT / "prompts" / "license_extraction.md"
KO_PATH = ROOT / "config" / "knockout_questions.json"
TH_PATH = ROOT / "config" / "scoring_threshold.json"


def banner(text: str, char: str = "=", w: int = 70) -> None:
    print()
    print(char * w)
    print(f"  {text}")
    print(char * w)


def main() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    scorer = MockScorer()
    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    knockouts = load_knockouts(KO_PATH)
    threshold = load_threshold(TH_PATH)
    store = PendingInsuranceStore(OUT_DIR / "_PendingInsurance.json")

    insurance_agent = {"name": "Alex Rivera", "email": "agent@insurance.example.com"}
    owner = {"name": "Operations Lead", "email": "owner@fcm.example.com"}

    # --- Scenario 1: process each application ---------------------------
    banner("Scenario 1 — FCM Hiring Pipeline (5 applicants)")
    apps_processed = []
    for path in sorted(APP_DIR.glob("jf_*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        submission = JotformSubmission(**raw)
        result = process_application(
            submission=submission,
            scorer=scorer,
            prompt=prompt,
            knockouts=knockouts,
            threshold_config=threshold,
            email_dir=EMAIL_DIR,
            output_dir=OUT_DIR,
            state_store=store,
            insurance_agent=insurance_agent,
            owner_email=owner["email"],
        )
        apps_processed.append(result)
        print(f"  {submission.submission_id}  {submission.first_name} {submission.last_name:<10s}"
              f"  role={submission.role_applying_for.value:<7s}"
              f"  decision={result.decision.value:<22s}"  # type: ignore[union-attr]
              f"  scores={result.scores.model_dump() if result.scores else {}}")
    print()
    print(f"PendingInsurance store: {len(store.pending_only())} pending candidate(s)")

    # --- Scenario 2: owner clears one candidate (jf_001) ----------------
    banner("Scenario 2 — FCM Insurance Loop (owner clears Marcus Johnson)")
    now2 = datetime(2026, 5, 22, 10, 30)
    cleared = clear_candidate(
        store=store,
        candidate_id="jf_001",
        cleared_by=owner["email"],
        now=now2,
        output_dir=OUT_DIR,
        email_dir=EMAIL_DIR,
        calendly_link="https://calendly.com/fcm/interview",
    )
    print(f"  cleared:    {cleared.candidate_full_name}  at {cleared.cleared_at}")
    print(f"  artifact:   data/output/{cleared.candidate_id}/gmail_congrats.txt")

    # --- Scenario 3: fast-forward to 24h, then 48h ----------------------
    banner("Scenario 3 — FCM Insurance Nudges (simulating 24h + 48h cron runs)")
    # Force `requested_at` back in time so the nudge thresholds trigger.
    diane = store.get("jf_005")
    if diane:
        diane.requested_at = datetime.now() - timedelta(hours=25)
        store._records["jf_005"] = diane   # type: ignore[attr-defined]
        store._save()                       # type: ignore[attr-defined]

    print("[+24h check] sending candidate update to anyone pending > 24h")
    summary_24 = run_nudges(
        store=store, now=datetime.now(),
        output_dir=OUT_DIR, email_dir=EMAIL_DIR,
        owner_name=owner["name"], owner_email=owner["email"],
        insurance_agent_name=insurance_agent["name"],
    )
    print(f"  nudged 24h: {summary_24['nudged_24h']}")

    if diane:
        diane = store.get("jf_005")
        diane.requested_at = datetime.now() - timedelta(hours=49)  # type: ignore[union-attr]
        store._records["jf_005"] = diane   # type: ignore[index,attr-defined]
        store._save()                       # type: ignore[attr-defined]

    print("[+49h check] sending 48h patience + owner escalation")
    summary_48 = run_nudges(
        store=store, now=datetime.now(),
        output_dir=OUT_DIR, email_dir=EMAIL_DIR,
        owner_name=owner["name"], owner_email=owner["email"],
        insurance_agent_name=insurance_agent["name"],
    )
    print(f"  nudged 48h: {summary_48['nudged_48h']}")
    print(f"  artifacts:  data/output/jf_005/gmail_nudge_48h_*.txt")

    # --- Scenario 4: Calendly booking watcher --------------------------
    banner("Scenario 4 — FCM Calendly Booking Watcher (build reminder schedule)")
    interview_at = datetime(2026, 5, 26, 14, 0)
    schedule = build_reminder_schedule(
        candidate_id="jf_001",
        candidate_first_name="Marcus",
        candidate_email="marcus.johnson@example.com",
        candidate_phone="+15555550100",
        interview_at=interview_at,
        now=datetime(2026, 5, 22, 11, 0),
    )
    print(f"  interview at:  {interview_at}")
    print(f"  reminders scheduled:")
    for r in schedule:
        print(f"    {r.cadence:>6s}  fires at {r.fires_at:%Y-%m-%d %H:%M}  via {r.channel}")

    # Persist the reminder schedule alongside the candidate dossier
    sched_out = OUT_DIR / "jf_001" / "reminder_schedule.json"
    sched_out.write_text(
        json.dumps([r.model_dump(mode="json") for r in schedule], indent=2, default=str),
        encoding="utf-8",
    )

    # --- Audit summary --------------------------------------------------
    banner("Audit summary")
    by_decision: dict[str, int] = {}
    for app in apps_processed:
        d = app.decision.value if app.decision else "unknown"   # type: ignore[union-attr]
        by_decision[d] = by_decision.get(d, 0) + 1
    print("Decisions by outcome:")
    for d, n in sorted(by_decision.items()):
        print(f"  {d:30s} {n}")
    print()
    print(f"Per-applicant artifacts under data/output/<submission_id>/")
    print(f"  decision.json, gmail_*.txt, reminder_schedule.json (for jf_001)")
    print(f"Pending insurance store: data/output/_PendingInsurance.json")


if __name__ == "__main__":
    main()
