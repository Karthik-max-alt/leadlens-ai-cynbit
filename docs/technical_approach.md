# Technical Approach Report — LeadLens AI

## 1. System goal

LeadLens helps an internal reviewer turn an unstructured project inquiry into a structured discovery record. It is a decision-support tool, not a sales-conversion predictor, auto-responder, CRM integration, or live Cynbit system.

## 2. Architecture

```text
Streamlit UI
  ├─ Role-based sign-in (Admin / Sales / Analyst)
  ├─ Inquiry workbench / CSV batch intake / pipeline / dashboard / evaluation lab
  └─ Human review + explicit save/update actions
          │
          ▼
Application layer
  ├─ Input validation and request limits
  ├─ Deterministic phrase-based extraction baseline
  ├─ Optional LLM structured extraction (OpenAI-compatible API)
  ├─ Output normalization + allow-listed service categories
  ├─ Explainable scoring + missing-field questions
  └─ Local discovery pack templates / optional LLM wording
          │
          ▼
SQLite prototype store
  ├─ users (salted password hash, role, active state)
  ├─ leads (analysis, stage, owner, follow-up, notes, exact fingerprint)
  └─ audit_events (actor, action, record id, change metadata)
```

The prototype is deliberately single-process. For production, move the data and authorization logic behind a service/API boundary, use managed PostgreSQL with migrations/backups, and review identity/session controls. SQLite on free/ephemeral hosting may be lost on a restart or redeploy.

## 3. Model and rules selection

### Deterministic baseline

The local extractor uses conservative phrase and regex rules for service routes, common requirements, industry hints, timeline, budget, integrations and missing fields. It can run without an API key, has low latency, is easy to inspect, and provides a reliable fallback for the assessment demo.

The deterministic baseline is not trained ML. A separate TF-IDF + Logistic Regression route candidate is included as a small ML experiment. It trains on 88 handcrafted synthetic examples and is compared with the deterministic keyword route on 28 distinct, independently authored synthetic holdout examples. This creates a reproducible model-vs-rules demonstration without pretending synthetic records are Cynbit data. It does not estimate conversion likelihood. The deterministic route may return “Unclear / discovery needed” rather than force a low-evidence category.

### Optional LLM extraction

When `OPENAI_API_KEY` is configured and the user explicitly selects LLM mode, the prototype calls the configured chat model (default `gpt-4o-mini`) using a JSON-object response format and temperature 0. The prompt asks the model to extract only supported facts, return null for unstated facts, use an allow-listed service taxonomy, and treat inquiry text as untrusted data. Provider calls have timeouts and a best-effort fallback to local extraction.

The UI identifies the engine used. LLM output is normalized: category values are checked against an allow-list; strings and arrays are bounded; malformed outputs or provider exceptions use the local baseline. This is useful defensive behavior, but not a substitute for formal JSON Schema validation, provider testing, or red-team review.

### Transparent triage score

Five deterministic components are exposed: requirement clarity, service fit, timeline/urgency evidence, implementation-scope evidence, and information completeness. The sum is capped between 0 and 100, then converted into low/medium/high review-order flags.

It is not a conversion probability. The app shows component scores and the relevant evidence phrases, makes a category override possible, and requires a human save action.

## 4. Prompt engineering

The extraction prompt follows these principles:

1. **Defined task:** extract factual fields for a human business/technical reviewer.
2. **Untrusted source data:** the prospect's words may contain instructions; treat them only as the content being analyzed.
3. **No fabrication:** do not invent budget, urgency, outcomes, integrations, or deadlines; use null when absent.
4. **Bounded taxonomy:** service category must be in a known set, otherwise fall back to local routing.
5. **Structured output:** return a JSON object with a fixed set of fields.
6. **No tools or external actions:** the LLM cannot send an email, accept a project, create a contract, or access the database.
7. **Human review:** final route and all customer-facing language remain editable drafts.

The discovery-pack prompt asks for an email draft, agenda, scope outline and success metrics, and explicitly prohibits prices, delivery commitments, or claims not supported by the supplied context. Generated output is size-bounded and always marked as draft-only. The local template path is used if the key is absent or the call fails.

## 5. Data pipeline

### Single inquiry

1. Accept 12–6,000 characters and optional bounded metadata.
2. Run deterministic extraction or the explicitly selected LLM path.
3. Normalize output and fill missing information conservatively.
4. Compute transparent triage components and tailored discovery questions.
5. Show evidence, unknowns and model source.
6. Let the reviewer override the category; recompute the heuristic score if the category changes.
7. Check exact duplicate fingerprint and require explicit confirmation if a possible duplicate exists.
8. Save record and audit event only after a human action.

### Bulk CSV

The batch interface requires an `inquiry` column and supports optional `company`, `contact_email`, and `source`. It caps the upload at 2 MB and 50 rows, uses local deterministic extraction by default, previews results before saving, skips exact duplicate fingerprints, and creates an audit event. Bulk input is not sent to an LLM.

### Stored records

SQLite contains user accounts, lead metadata and serialized analysis, and audit events. The application does not intentionally put raw inquiry text into audit event details. Contact fields are optional and validated. Demo starter leads are synthetic and marked as demos. Admin/Sales can export lead data; the Analyst UI hides contact email and raw inquiry text.

**Important:** SQLite plus UI role gating is appropriate for an assessment demonstration only. The implementation is not a formal security boundary for a multi-tenant production system.

## 6. Login and role model

Passwords are salted and hashed with PBKDF2-HMAC-SHA256 (310,000 iterations). Roles:

- **Admin:** user administration, lead deletion, full pipeline access, exports and audit history.
- **Sales:** analyze/create, update pipeline, assign owners, schedule follow-ups, use CSV intake and export leads.
- **Analyst:** overview, evaluation lab and read-only pipeline without contact email/raw inquiry details.

Demo mode seeds documented synthetic demo accounts only when the user table is empty. For a non-demo environment, set `LEADLENS_DEMO_MODE=false` and use a fresh database; a first-run administrator setup appears. Do not use public demo credentials with real customer information.

The login cooldown is session-level and intentionally small. It is not distributed server-side rate limiting. A production deployment must add an identity provider or hardened auth service, secure cookie/session configuration, CSRF review, persistent auditing, lockout protection, and an API-side permission check.

## 7. Additional workflow features

- Pipeline stages: New, Contacted, Discovery Scheduled, Qualified, Proposal, Won, Lost, On Hold.
- Owner assignment, follow-up dates, notes and due/overdue indicators.
- Exact normalized duplicate fingerprint: repeated same contact/company/inquiry is flagged; it is not semantic/fuzzy deduplication.
- CSV import with preview, local batch analysis, duplicate skipping and export.
- Draft discovery email, meeting agenda, scope assumptions/out-of-scope items and success metrics.
- Admin user provisioning/deactivation and temporary reset credentials.
- Audit trail for major login, analysis, lead, and user-management events.

## 8. Evaluation plan

### Included smoke test

The repository includes a six-inquiry deterministic smoke test and an 88-example ML training set with 28 distinct holdout examples. At package validation, the rules baseline matched 6/6 simple smoke cases. The ML candidate matched 27/28 holdout cases; keyword rules matched 14/28. These are **handcrafted synthetic results only**, not a representative dataset, measured customer accuracy, or a generalization claim. The holdout includes ambiguous/multi-scope requests to inspect failure modes.

### Recommended pilot

Create a reviewed set of 100–300 permissioned/consented inquiries across service lines, including vague, multi-intent, typo-heavy, adversarial and missing-field cases. Split a held-out set before tuning prompts/rules. Report:

- macro-F1, per-class precision and recall for service category;
- field-level precision/recall or exact match for budget/timeline/industry/requirements/integrations;
- unsupported-fact rate from reviewer audit;
- missing-field recall and usefulness ratings for discovery questions;
- human edit/override rate and median preparation time;
- latency, provider failure/fallback rate, malformed-output rate;
- exact duplicate false-positive/false-negative review.

Do not optimize only for aggregate routing accuracy. Review errors by class and by missing-information pattern. No trained outcome model should be considered until a reliable, consented historical dataset exists and its use is approved.

## 9. Security, privacy and reliability

- Public demo uses synthetic records and public demo credentials; it must not collect real customer data.
- `.env` is gitignored; do not commit API keys or database files.
- External LLM calls are optional and user-selectable; organizational approval is required before sending any non-public inquiries.
- Use parameterized SQL, output bounds and controlled status/category lists.
- No email sending, purchase, contract acceptance, automated rejection or other external action exists.
- Session-scoped login throttle, UI role checks and SQLite audit log are prototype-level safeguards only.
- For actual use: managed PostgreSQL, backups, migrations, encryption and secrets management, centralized identity, server-side rate limiting, formal data retention/deletion policy, access reviews, monitoring and security testing are required.

## 10. Deployment

Local setup: `pip install -r requirements-dev.txt`, copy `.env.example` to `.env`, then run `streamlit run app.py`. Test using `pytest -q` and `python scripts/evaluate.py`.

Render configuration is in `render.yaml` and starts Streamlit on the platform-provided port. The Blueprint is configured for an assessment demo on the free web-service plan; its SQLite data can be reset during host restart/redeploy. Evaluate current host pricing and select durable storage before using it for a persistent pilot.

## 11. Next steps

1. Confirm intake workflow and service taxonomy with Cynbit stakeholders.
2. Run a reviewed shadow test against human outputs.
3. Fix routing/extraction errors and improve evidence display.
4. If value is demonstrated, move storage and auth to durable, reviewed infrastructure.
5. Integrate with a CRM only with narrow scoped credentials and human approval requirements.
