# Cynbit Assessment Submission Notes

## Suggested primary link

GitHub repository: `https://github.com/<YOUR_USERNAME>/leadlens-ai-cynbit` (replace with the real repository URL after creating and pushing it).

## Suggested additional link

Live Render demo: `<YOUR_RENDER_URL>` (replace only after the deployment has succeeded and the app has been tested).

## Optional execution notes & rationale

LeadLens AI is a proposed human-in-the-loop inquiry-to-discovery copilot based on Cynbit's publicly described service and product portfolio. It transforms an unstructured project inquiry into an evidence-backed summary, likely service route, requirement signals, a transparent triage score, missing-information questions, and a discovery pack for a human reviewer.

The proof of concept includes role-based accounts (Admin, Sales and Analyst), salted password hashing, pipeline tracking, assignment/follow-up reminders, exact-duplicate warnings, CSV batch intake, optional structured LLM extraction with deterministic fallback, draft email/agenda/scope generation, an audit trail, and a synthetic evaluation lab. It is configured for VS Code, GitHub Actions, and Render.

The included six-example route suite is a handcrafted synthetic smoke test only; it does not establish production accuracy. The demo uses synthetic data, does not send customer-facing communications, and requires human review. A shadow pilot with approved/consented inquiries should establish utility, extraction grounding, routing quality and review-time impact before integration with Cynbit systems.

## Pre-submit checklist

- [ ] Run `pytest -q` locally; all tests pass.
- [ ] Run `python scripts/evaluate.py` and retain the caveat about six synthetic examples.
- [ ] Launch with `streamlit run app.py` and test all available screens.
- [ ] Test Admin, Sales and Analyst login; confirm Analyst cannot see contact email/raw inquiry in the UI.
- [ ] Test analysis, category override, saving, duplicate warning, status updates, follow-up dates, CSV import/export, discovery pack, audit trail and password change.
- [ ] Check `.env`, API keys and SQLite files are not committed.
- [ ] Push the repository and verify its README, reports, tests and `.github/workflows/tests.yml`.
- [ ] Deploy on Render and test the actual public URL; do not submit an unverified URL.
- [ ] Use only synthetic data in the publicly accessible demo and disclose that hosting storage may reset.
