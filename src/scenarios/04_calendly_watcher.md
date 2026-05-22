# Scenario 4: FCM Calendly Booking Watcher

**Trigger:** Calendly `invitee.created` webhook.

## Make module order

| # | Module | Notes |
| --- | --- | --- |
| 1 | **Custom webhook (Calendly)** | Configured on the Calendly event type |
| 2 | **Parse fields** | Extract candidate email, name, phone, interview start time |
| 3 | **Compute schedule** | Build the four reminder firing times — see Python `src/reminders.py::build_reminder_schedule` |
| 4 | **Iterator** | Loop the four reminders |
| 5 | **Sleep until `fires_at`** | Use Make's "Sleep" module — Make supports up to 5 minute waits per call, so chain or use a data store + scheduled job for the long waits. *(Implementation note: production uses a "ScheduledReminders" data store with hourly cron checking due reminders rather than long Make sleeps — more reliable.)* |
| 6a | **Twilio send SMS** | If channel includes "sms". Body from `config/sms_templates/reminder_{cadence}.md` |
| 6b | **Gmail send** | If channel includes "email" |

## Cadence

| Offset before interview | Channels |
| --- | --- |
| 48 hours | email + SMS |
| 24 hours | email + SMS |
| 2 hours  | SMS only |
| 30 min   | SMS only |

## What the Python repo provides

- `src/reminders.py::build_reminder_schedule` — produces the four reminder records given an interview time and "now". Reminders that would fire in the past are skipped (handles late-booked interviews gracefully).
- All four SMS body templates.
- The cadence definition in code form so it's easy to tune without scenario rebuilding.
