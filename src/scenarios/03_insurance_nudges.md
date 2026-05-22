# Scenario 3: FCM Insurance Nudges

**Trigger:** Hourly cron (Make's built-in scheduler).

## Make module order

| # | Module | Notes |
| --- | --- | --- |
| 1 | **Scheduler** | Every hour, on the hour |
| 2 | **Data store search — PendingInsurance** | All records with `cleared_at = null` |
| 3 | **Iterator** | Loop over each pending candidate |
| 4 | **Router** | Branch on hours-since-requested |
| 4a | **24h branch:** if `requested_at <= now - 24h` AND `nudged_24h = false` |
| 5a | **Gmail (candidate 24h update)** | Body: `config/email_templates/nudge_24h.md` |
| 6a | **Data store update** | `nudged_24h = true` |
| 4b | **48h branch:** if `requested_at <= now - 48h` AND `nudged_48h = false` |
| 5b | **Gmail (candidate 48h patience)** | Body: `config/email_templates/nudge_48h_candidate.md` |
| 5c | **Gmail (owner escalation)** | Body: `config/email_templates/nudge_48h_owner.md` |
| 6b | **Data store update** | `nudged_48h = true` |

## Why the boolean flags matter

Without `nudged_24h` / `nudged_48h`, every hourly run would resend the same email to candidates whose insurance still isn't cleared. The flags make this idempotent.

## What the Python repo provides

- `src/insurance_loop.py::run_nudges` — same logic, callable on demand for testing.
- The three email templates.
- `src/state_store.py::needing_24h_nudge` / `needing_48h_nudge` — exact filter logic.
