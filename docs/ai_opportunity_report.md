# AI Opportunity Report — Cynbit Technologies

**Project:** LeadLens AI — Inquiry-to-Discovery Copilot  
**Prepared for:** AI/ML Engineer Intern assessment  
**Date:** 20 October 2026  
**Research boundary:** Public Cynbit pages and a proposed workflow hypothesis only. No access to internal performance, sales, client, or product data was available.

## 1. Executive recommendation

Build and evaluate a human-in-the-loop inquiry-to-discovery copilot that converts a prospective client's unstructured project description into a structured, reviewable discovery brief. The tool should identify a likely service route, surface requirements and missing information, show why a triage score was assigned, and draft discovery questions and a proposed next step.

This is a **testable opportunity hypothesis**, not a claim that Cynbit has confirmed a sales bottleneck or currently loses leads. Public pages describe multiple services and products and include a project inquiry workflow. A common intake workbench could be worth validating because early project requests may span several service lines and vary considerably in completeness.

**Recommendation:** run a shadow pilot on synthetic or explicitly approved/consented inquiries. Measure reviewer time, fact grounding, routing quality and usefulness before considering integrations or any automated external action.

## 2. Public business context

Cynbit's public website describes software and AI services and a product portfolio that includes:

- **Cynbit Studio:** a career-development / coding-practice platform.
- **Revio:** reputation and review management.
- **TenantEase:** property-operations / tenant-management workflows.
- **AI, software and cloud delivery:** potential services for clients with bespoke project needs.

The public website is not a source of internal operating metrics. The analysis therefore does not assume a particular number of inbound inquiries, a response-time problem, an underperforming sales funnel, or an existing CRM configuration.

Public source links:

1. [Cynbit homepage](https://www.cynbit.in/)
2. [Services](https://www.cynbit.in/services)
3. [Product Suite](https://www.cynbit.in/products)
4. [Contact / inquiry page](https://www.cynbit.in/contact)
5. [About Cynbit](https://www.cynbit.in/story)

## 3. Opportunity landscape

| Candidate opportunity | Potential value | Feasibility | Data dependency | Key risk |
|---|---|---|---|---|
| **Inquiry-to-discovery copilot** (selected) | Consistent intake, better-prepared discovery calls, less repeated manual parsing | High for a workflow PoC | Inquiry text, service taxonomy, reviewer feedback | Unsupported facts or misleading lead score |
| Revio review-theme intelligence | Summarize recurring customer concerns across locations; highlight changes in themes | High for an offline demonstration | Authorized review text, source, date, location and human labels | Tone errors, privacy, source/platform constraints |
| Cynbit Studio learning-path recommender | Suggest targeted learning content based on observed skill gaps | Medium | Skill taxonomy, exercise outcomes, learner consent | Unfair skill inference or poor recommendations |
| TenantEase document and maintenance assistant | Extract lease/maintenance details and prepare tasks for review | Medium | Authorized records, role access, property metadata | Exposure of personal/financial data; mistaken dates or obligations |
| Internal engineering knowledge assistant | Retrieve approved runbooks, architecture decisions and implementation notes | Medium-high after document owners and permissions are confirmed | Versioned, access-controlled internal documents | Stale information, hallucinations or access leakage |
| Marketing performance insight assistant | Group feedback, summarize funnel trends, draft experiment hypotheses | Medium | Consistent analytics events and campaign definitions | Correlation presented as causation |

### Selection rationale

The inquiry copilot wins for this assessment because it is directly adjacent to a publicly visible inquiry workflow, can demonstrate a useful multi-stage pipeline without access to confidential data, can be evaluated through human review, and has a clear safe boundary: no automatic messaging, pricing, commitment, or rejection.

## 4. Problem framing

**Primary user:** a business-development, solution-consulting, or engineering-team member who reviews a new project inquiry.

**Job to be done:** “Help me understand what the prospect actually asked for, distinguish known facts from unknowns, and prepare a better first discovery conversation.”

**Input:** a prospect's project description and optional organization/contact/source metadata.

**Output:**

- concise summary and probable Cynbit service/product route;
- requirements and integration signals grounded in the inquiry;
- industry, timeline and budget only when stated or supported by the configured extraction process;
- missing information and tailored discovery questions;
- a transparent triage score with component-level evidence;
- a draft email, meeting agenda and scope outline for human review;
- a saved pipeline record with owner, status, follow-up date, notes and change history.

## 5. Proposed product: LeadLens AI

### User experience

1. **Capture:** enter one inquiry or upload a small CSV batch.
2. **Structure:** extract service route, requirements, context, timeline, budget, integrations and unknowns.
3. **Review:** show the evidence, rule components, urgency phrases and missing fields.
4. **Prepare:** generate discovery questions, a draft response, an agenda and a scope outline.
5. **Route:** a human confirms or overrides the category and saves the record.
6. **Follow through:** manage assignment, pipeline state, due dates, notes and audit events.
7. **Evaluate:** inspect synthetic routing results and export the test report.

### Role model

| Role | Use case | Access boundary |
|---|---|---|
| Admin | Manage workspace users and review the audit trail | Can manage users, view contact details, export records and delete records explicitly |
| Sales | Analyze inquiries, assign owners, schedule follow-ups and update pipeline state | Can create and edit lead records; no team administration |
| Analyst | Understand distribution, routing and pipeline status | Read-only; contact fields and raw inquiry text are hidden in the UI |

The role model is a deliberate assessment feature. The current implementation is a single-process Streamlit prototype. A production system would enforce authorization in a service/API layer and use a durable identity provider where appropriate.

## 6. Triage score: transparent, not predictive

The prototype scores five rule-based components, totalling up to 100 points:

- requirement clarity (up to 25);
- service fit (up to 20);
- timeline / urgency evidence (up to 20);
- implementation-scope evidence (up to 20);
- information completeness (up to 15).

Priority bands determine suggested review order. The output is **not** a model of conversion probability, a judgment about a person, or a reason to reject a prospect. A clear small request could be valuable; a complex urgent request could be a poor fit. All decisions remain with a human reviewer.

## 7. Expected value and measurement

No ROI, time saving or conversion improvement is claimed without a pilot. Establish the current human baseline first, then compare it with the tool using the same representative set.

| Dimension | Metric | Measurement method |
|---|---|---|
| Routing quality | Category macro-F1, per-class precision/recall | Compare predicted route with reviewed labels on a held-out dataset |
| Extraction quality | Field precision/recall or exact match | Review budget, timeline, industry, requirements and integrations |
| Grounding | Share of extracted facts supported by source | Audit a random sample of output claims against inquiry text |
| Usefulness | Reviewer rating and edit/override rate | Short post-review feedback form and event log |
| Efficiency | Median preparation time | Paired timed human-only vs assisted tasks |
| Reliability | Latency, provider-fallback rate, malformed-output rate | Application-level metrics with no raw inquiry logging |
| Safety | Unsupported deadlines/prices, mistaken duplicate merges | Adversarial and edge-case test set plus reviewer audit |

**Proposed pilot gates (targets only; not achieved results):** at least 90% of audited extracted claims supported by the source; at least 0.80 category macro-F1 on a representative reviewed set; and no unsupported budget or deadline accepted without review. Adjust thresholds after observing task stakes and baseline performance.

## 8. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Fabricated requirements or deadlines | Return null / “not stated” for unknown fields; validate types and service categories; human confirms the route |
| Prompt injection in inquiry text | Treat the source text as untrusted data; no model tools or external actions; validate generated structure; review drafts |
| Over-reliance on a numerical score | Show component evidence and disclaimers; no automated rejection or pricing |
| Accidental contact / commitment | Drafts are never sent; no send-email integration is present |
| Sensitive data leakage | Use synthetic examples in public demo; disable external LLM by default when no key exists; explicit checkbox when configured; review provider and retention settings before a pilot |
| Role leakage | Separate roles in the UI; hide contact details/raw inquiry for Analyst; test access paths; move authorization server-side before production |
| Duplicate data | Exact normalized fingerprints and an explicit warning; no fuzzy semantic merges |
| Lost records on hosted restart | Document SQLite's ephemeral-host limitation; use managed durable storage and backups in an approved pilot |
| Misleading evaluation | Label the six-example suite as synthetic smoke test; collect a representative, reviewed and held-out dataset before claiming performance |

## 9. Execution plan

**Phase 1 — Workflow validation (1–2 stakeholder sessions):** confirm inquiry owners, service taxonomy, required fields, current follow-up process, data policy and what makes a brief useful.

**Phase 2 — Shadow test:** run on synthetic or approved/consented inquiries. Keep the workflow independent of customer treatment. Compare outputs to human-reviewed labels and log corrections.

**Phase 3 — Improve:** update service-routing phrases and extraction prompts based on observed errors; improve discovery questions; inspect false duplicates and fallback frequency.

**Phase 4 — Integrate selectively:** if the value hypothesis is supported, connect to the CRM through scoped credentials and access-controlled persistent storage. Human approval remains required for any customer-facing output.

**Phase 5 — Monitor:** record model/prompt version, routing, reviewer changes, latency, and fallback state; review errors, drift and access logs on a regular cadence.

## 10. Scope and limitations of this proof of concept

Implemented: Streamlit workflow, deterministic extraction and scoring, a separate TF-IDF + Logistic Regression route candidate (trained on 88 synthetic examples and compared on 28 distinct synthetic holdout examples), optional OpenAI structured extraction/drafting, role-based login and salted password hashes, pipeline management, assignment and follow-up dates, exact duplicate detection, CSV batch intake, downloadable outputs, audit trail, synthetic evaluation lab, tests and Render configuration. On this handcrafted holdout the ML candidate matched 27/28 cases while the keyword baseline matched 14/28; this is a tiny, synthetic implementation check—not an accuracy or generalization claim.

Not production-complete: managed database, backups and migrations; centralized identity/SSO; server-side distributed rate limiting; formal retention/deletion policy; security review; monitoring/alerting; durable multi-instance coordination; and real Cynbit-system integration.

## Conclusion

LeadLens is designed to demonstrate a practical AI-assisted workflow without overstating the model. The distinctive contribution is the combination of extraction, transparent triage, unknown-field discovery, collaboration workflow, role-based access and evaluation. The right next step is a measured shadow pilot with Cynbit stakeholders, not an immediate automated sales decision.
