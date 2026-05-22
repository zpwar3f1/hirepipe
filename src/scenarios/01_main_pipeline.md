# Scenario 1: FCM Hiring Pipeline

**Trigger:** Jotform submission webhook (already configured per the brief).

## Make module order

| # | Module | Notes |
| --- | --- | --- |
| 1 | **Custom webhook** | Already exists; receives Jotform payload |
| 2 | **Anthropic Claude (vision)** | System prompt: `prompts/license_extraction.md`. Model: `claude-sonnet-4-5`. User message: license image (from Jotform upload URL) + applicant answers concatenated. Variable-picker mapping for Jotform fields needs fixing in the existing scenario — the brief flagged this. |
| 3 | **Parse JSON** | Schema matches the output in `prompts/license_extraction.md` |
| 4 | **Router — knockouts** | Five filters checking the knockout fields from `config/knockout_questions.json` |
| 5a | **Gmail send (rejection)** | If any knockout fails. Body: `config/email_templates/rejection.md` |
| 5b | **Router — scores** | Checks all four scores ≥ 8 |
| 6a | **Gmail send (rejection)** | If any score < 8 |
| 6b | **Router — role branch** | Driver vs mover (mover skips insurance, goes straight to interview scheduling) |
| 7a | **Gmail send (insurance request)** | To insurance agent. Body: `config/email_templates/insurance_request.md` |
| 7b | **Gmail send (screening update)** | To candidate. Body: `config/email_templates/screening.md` |
| 7c | **Data store write — PendingInsurance** | Add candidate with `requested_at = now` |
| 7d | **Gmail send (congrats)** | (mover path) — `config/email_templates/congrats_calendly.md` |

## Variable contract from Claude module to downstream

```json
{
  "license": { "license_number", "full_name", "dob", "expiration_date",
                "state", "class", "endorsements", "restrictions",
                "extraction_confidence" },
  "scores":  { "experience", "availability", "professionalism", "physical_capability" },
  "score_rationale": { same four keys },
  "concerns": ["array of strings"]
}
```

## What the Python repo provides

- `src/pipeline.py::process_application` — same routing logic in code form for testing.
- The exact prompt that goes into the Claude module.
- The structured-output schema for Parse JSON.
- All five Gmail body templates with variable placeholders.
