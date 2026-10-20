# LeadLens AI — Cynbit AI/ML Engineer Intern Assessment

**An inquiry-to-discovery copilot concept for Cynbit.** LeadLens converts a project inquiry into an evidence-backed summary, a likely service route, transparent triage signals, missing-information questions, and a human-reviewed discovery pack. It is a proposed proof of concept, not a live Cynbit product and not a claim that Cynbit has confirmed an intake bottleneck.

## Why this can stand out

This submission is designed as a small internal product, not a single LLM prompt. It includes:

- Role-based access: **Admin**, **Sales**, and **Analyst**.
- Password storage using salted PBKDF2-HMAC-SHA256 hashes; no plaintext password storage.
- Admin user provisioning, deactivation/reactivation, and temporary password reset.
- Analysis workbench with service routing, requirement signals, budget/timeline/integration extraction, missing-field detection, urgency evidence, and score breakdown.
- Separate TF-IDF + Logistic Regression routing candidate trained on 88 handcrafted synthetic examples, compared against the rules baseline on 28 independently authored synthetic holdout cases; disagreement is surfaced for human review.
- Human category override and duplicate warning before saving.
- Pipeline states: New → Contacted → Discovery Scheduled → Qualified → Proposal → Won / Lost / On Hold.
- Owner assignment, follow-up dates, internal notes, filtered search, and due/overdue reminders.
- Bulk CSV intake (up to 50 rows per batch), analysis preview, duplicate skipping, JSON/CSV exports.
- Draft client email, discovery agenda, scope outline, and success metrics. **No message is sent.**
- Admin audit trail for login events, lead creation/updates/deletions, user changes, and pack generation.
- Evaluation lab with a handcrafted synthetic smoke test, explicit caveats, and a prompt-injection boundary demonstration.
- Optional OpenAI structured extraction and drafting with deterministic local fallback if no key is configured or the provider fails.
- Tests, GitHub Actions CI, and Render Blueprint deployment configuration.

## Quick start in VS Code (Windows PowerShell)

1. Extract the ZIP and open the `leadlens-ai` folder in VS Code.
2. Open Terminal → New Terminal.
3. Create a virtual environment and install dependencies:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
streamlit run app.py
```

Open the local address Streamlit prints (normally `http://localhost:8501`). Demo mode is enabled in `.env.example`; no API key is required.

### Demo login accounts

These accounts are intentionally public so a reviewer can exercise each role. The app seeds synthetic demo records on a new database.

| Role | Username | Password |
|---|---|---|
| Admin | `demo_admin` | `AdminDemo!2026` |
| Sales | `demo_sales` | `SalesDemo!2026` |
| Analyst | `demo_analyst` | `AnalystDemo!2026` |

**Do not use demo credentials with real client data.** Public credentials are only for an isolated assessment/demo deployment. Demo mode intentionally seeds examples for a reviewer walkthrough.

## Role permissions

| Capability | Admin | Sales | Analyst |
|---|---:|---:|---:|
| Executive overview and evaluation lab | ✓ | ✓ | ✓ |
| Analyze and create lead | ✓ | ✓ | — |
| View/change pipeline, assign owner and follow-ups | ✓ | ✓ | Read-only |
| Contact email and original inquiry visibility | ✓ | ✓ | Hidden in UI |
| Bulk CSV import and PII export | ✓ | ✓ | — |
| Create/deactivate users and temporary password reset | ✓ | — | — |
| View audit trail and delete records | ✓ | — | — |
| Change own password | ✓ | ✓ | ✓ |

## Optional LLM setup

Local deterministic extraction and templates work without an API key. To enable optional LLM-assisted extraction/drafting, set `OPENAI_API_KEY` in `.env` or your host's secret/environment settings. The UI makes provider use explicit. When enabled, inquiry text may be sent to the configured provider. Do not send confidential or personal data without organizational approval. Provider errors fall back to local behavior.

`OPENAI_MODEL` defaults to `gpt-4o-mini`; set it to a model available to your account. Never commit `.env` or an API key.

## Run tests and the synthetic evaluation

```powershell
pytest -q
python scripts/evaluate.py
```

The included six-row routing suite and the 88-example training / 28-example holdout for the ML router are **handcrafted synthetic data**. The holdout metrics only show how this prototype behaves on a small controlled set; they are not representative and do not establish production accuracy or generalization. See `docs/technical_approach.md` for the evaluation plan.

## GitHub: publish your project

Create an **empty** GitHub repository first (do not add a README or license from GitHub, because this folder already contains them). From the project folder:

```powershell
git init
git add .
git commit -m "Build LeadLens AI inquiry intelligence PoC"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/leadlens-ai-cynbit.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username. Check that `.env`, SQLite database files, and secrets are not included in the pushed repository.

## Render: deploy from GitHub

1. Push and verify the repo first.
2. Sign in to Render and choose **New → Blueprint**.
3. Connect your GitHub repo and select the included `render.yaml`.
4. Review the service configuration and deploy.
5. Open the generated URL, sign in using the demo credentials, and test Overview, Analyze & Create, Pipeline, Bulk Intake, Quality Lab, and Admin/Analyst role differences.

The included Blueprint uses a free web service and SQLite. **Free/ephemeral hosting storage may be reset on restarts/redeploys.** This is acceptable for an assessment demo but not reliable business storage. For a real pilot, use a managed persistent database (preferably PostgreSQL), configure backups, and review the host's current costs before provisioning any paid service.

### Turn off demo mode for a non-public environment

Use a **fresh database path** and set `LEADLENS_DEMO_MODE=false`; the app will present a first-run administrator setup screen rather than create public demo users. The prototype removes the three reserved demo accounts when demo mode is disabled, but does not automatically delete seeded lead data—use a new database for a clean environment. Do not deploy publicly with the default demo credentials if you plan to input real data.

## Project layout

```text
leadlens-ai/
├── app.py                    # Streamlit application and role-aware screens
├── leadlens.py               # Conservative extraction, scoring and analysis
├── leadlens_plus.py          # Discovery pack, urgency/tone cues, evaluation
├── ml_router.py              # TF-IDF + Logistic Regression candidate and benchmark
├── auth_store.py             # SQLite schema, password hashing, RBAC-related data APIs
├── data/
│   ├── sample_inquiries.json  # Six-case rules smoke test
│   ├── routing_train.json     # 88 synthetic route-training examples
│   └── routing_holdout.json   # 28 distinct synthetic holdout examples
├── docs/
│   ├── ai_opportunity_report.md
│   ├── technical_approach.md
│   └── submission_notes.md
├── scripts/evaluate.py
├── tests/
├── .env.example
├── requirements.txt
├── requirements-dev.txt
├── render.yaml
└── Procfile
```

## Important production gaps (stated honestly)

This is an assessment-grade, single-process prototype—not a production CRM. It uses SQLite, a session-level login throttle, and application-level role gating. Before a real multi-user deployment, add durable PostgreSQL storage, database migrations/backups, server-side rate limiting, secure session/CSRF review, secrets management, email/identity-provider integration, formal retention/deletion controls, and a security review. UI role hiding must not be treated as a substitute for a dedicated authorization layer in a larger application.

## Public research references

- [Cynbit homepage](https://www.cynbit.in/)
- [Cynbit services](https://www.cynbit.in/services)
- [Cynbit product suite](https://www.cynbit.in/products)
- [Cynbit contact / inquiry page](https://www.cynbit.in/contact)
- [Render web services documentation](https://render.com/docs/web-services)

Last authored for the assessment package: 20 October 2026.
