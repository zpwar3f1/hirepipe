# Scenario 2: FCM Insurance Loop

**Trigger:** Owner submits a small private Jotform with a single field:
"clear this candidate — paste their email".

## Make module order

| # | Module | Notes |
| --- | --- | --- |
| 1 | **Custom webhook** | Private Jotform with single email field |
| 2 | **Data store search — PendingInsurance** | Look up by `candidate_email` |
| 3 | **Router** | Found / not found |
| 4a | **Data store update** | Set `cleared_at = now`, `cleared_by = owner_email` |
| 4b | **Gmail send (congrats + Calendly)** | Body: `config/email_templates/congrats_calendly.md` |
| 5a | **Gmail send (owner alert)** | If candidate not found — alerts owner so they can investigate |

## Edge cases

- Candidate already cleared: no-op, log a warning.
- Candidate not in pending store: alert owner (probably already mailed or rejected).
- Multiple matches by email (shouldn't happen): clear all and log a deduplication task.

## What the Python repo provides

- `src/insurance_loop.py::clear_candidate` — runs the same flow.
- Reference congrats email template.
