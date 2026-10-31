# DECISIONS.md: Celebration & Event Planner

This document records the architectural and engineering decisions, sensible defaults, and trade-offs made during the development of the GenAI Celebration & Event Planner Assistant.

---

## 1. Deterministic Arithmetic & Financial Invariants (M1)
- **Decision**: All budget percentages, category allocations, and spend differences are computed in deterministic Python code. The LLM is never allowed to do arithmetic.
- **Rationale**: LLMs frequently introduce off-by-one errors, rounding inconsistencies, or negative allocations. The LLM provides relative category weight recommendations, which the deterministic engine normalizes:
  - Contingency is reserved first (clamped between 5.0% and 10.0%, default 8.0%).
  - Non-contingency categories are scaled to fill the remaining percentage.
  - Rounding differences are resolved deterministically so `sum(percentages) == 100.00%` and `sum(allocated_amount) == total_budget` to the exact cent.

---

## 2. Adaptive Timeline & Dynamic Sprint Compression (M2)
- **Decision**: The milestone generator adapts based on the lead time between `today` and `event_date`:
  - **>= 180 days (6-12+ months)**: Standard long-horizon milestones (12m, 6m, 4m, 3m, 2m, 1m, 2w, 1w, 1d, Day-Of).
  - **30 to 180 days (1-6 months)**: Accelerated milestone schedule.
  - **< 30 days (Ultra-rush sprint, e.g. 3 weeks, 1 week away)**: Automatically compresses the timeline into high-urgency sprint phases (Immediate, Sprint Phase 1, Final Countdown), flags critical bookings as `is_high_risk = True`, and sets `is_compressed = True`.
- **Date Clamping**: All milestone due dates are strictly clamped between `today` and `event_date`, sorted in chronological order. A day-of hourly run-of-show is always generated.

---

## 3. Mandatory Vendor Categories & 4-Item Checklists (M3)
- **Decision**: Defined strict mandatory vendor requirements per event type:
  - **Wedding**: Venue & Reception Hall, Catering & Drinks, Photography & Video, Decor & Flowers, Music & DJ / Live Band.
  - **Birthday**: Venue / Party Space, Cake & Catering, Entertainment / Host, Decor & Balloons.
  - **Community**: Venue / Public Grounds & Permits, Sound & AV Equipment, Catering & Refreshments, Security & Safety / First Aid.
- **Enforcement**: If the LLM omits any mandatory category, the deterministic repair layer injects it, complete with quotes linked to the budget and at least 4 verification checklist tasks (contract/license, initial deposit date, technical questions, final balance payment date, plus a backup vendor).

---

## 4. Dietary & Kid-Safety Guardrails (M4)
- **Decision**: Implemented an automated deterministic inspection filter on all personalized ideas:
  - **Vegetarian / Vegan / Jain**: Scrubs meat, fish, poultry, seafood. For Jain, scrubs root vegetables, onions, and garlic.
  - **Kids Parties / Demographics**: Scrubs alcohol, bar setups, and adult themes, replacing them with mocktail bars, fruit smoothies, and age-appropriate games.
  - **Budget Swaps**: Every idea item must have an actionable `budget_friendly_swap` (e.g., using local seasonal marigolds instead of imported orchids).

---

## 5. Offline Fallback & Graceful Degradation (M5, M7)
- **Decision**: If `GEMINI_API_KEY` is not provided in `.env`, or if the Gemini API experiences network timeouts or rate limits, the app seamlessly activates `FallbackTemplateEngine`.
- **Impact**: The app never crashes, never outputs an unhandled 500 error, and allows hackathon judges to test the complete application offline or without configuring an API key.

---

## 6. Hybrid AI Chat & Deterministic Command Engine (M6)
- **Decision**: The AI Assistant supports both natural language question answering grounded in the active plan data AND deterministic regex-assisted tool dispatching (`move_budget`, `adjust_event_date`, `update_vendor_status`, `update_task_status`, `add_custom_task`, `add_personalized_idea`).
- **Safety**: Every tool action executes through `DeterministicRepairEngine.repair_full_plan`, guaranteeing that the plan remains 100% valid after every single conversational change.

---

## 7. Unified Serving Architecture
- **Decision**: Built the frontend into `frontend/dist` and mounted it directly onto the FastAPI application at `/`.
- **Benefit**: Running `python start_app.py` or `make dev` serves both the API and the React Single Page Application on a single port (`8000`), eliminating CORS configuration issues and simplifying deployment and evaluation.

---

## 8. AI-Powered Smart Budget Optimizer
- **Decision**: Designed an extensible budget analysis and optimization pipeline (`SmartBudgetOptimizer` in `backend/app/budget_optimizer.py` and `GET /api/events/{id}/budget-analysis`, `POST /api/events/{id}/optimize-budget`):
  - **Budget Health Analysis**: Calculates total allocated vs remaining, category distribution, highest expense category, and high-impact potential savings targets without modifying database state.
  - **Natural-Language Goal & Constraint Parsing**: Accepts user instructions (e.g. "Reduce my wedding budget by ₹30,000", "Keep food quality high", "Save 15%").
  - **Zero Silent Mutations**: The optimizer generates a recommended proposal and comparison metrics (original vs recommended, difference, % change, side-by-side Recharts grouped bar chart) but NEVER silently updates the database. The user must review the proposal and explicitly click **Apply New Budget** (or **Discard Changes**).
  - **Deterministic Math & Constraint Guardrails**: Even when Gemini suggests weights, the LLM is never trusted with arithmetic. Reductions are applied to flexible categories, user-protected categories (e.g. catering) are preserved, contingency buffer (5-10%) remains intact, and weights are normalized by `DeterministicRepairEngine` ensuring `sum(items) == revised_total_budget` and `sum(percentages) == 100.00%`.
  - **Provider Transparency**: The API and UI explicitly report `engine_used` (`gemini` or `fallback_rule_engine`). AI responses are never faked.

---

## 9. Phase 2: Smart Expense Tracking & Planned vs Actual Ledger
- **Decision**: Implemented a relational `expenses` table (`ExpenseModel` in `backend/app/models.py`) with foreign key linkage and cascade deletion tied to `EventModel.id`.
- **Planned vs. Actual Integration**:
  - Dynamically calculates category variance, remaining funds, and overspending by contrasting live expense records against the active plan budget.
  - Preserves user expenses independently from budget optimizations: when a user reallocates or shrinks total budget via Phase 1 AI Budget Optimizer, previously logged expenses remain intact and are immediately compared against the revised budget ceiling.
  - Syncs `actual_spent` back to `EventModel.plan_json` so that `DashboardStats`, `BudgetTab`, and `ExpenseTab` maintain 100% real-time state coherence.
- **Intelligent Budget Alerts**:
  - Category-level overspending flags (`actual > planned`), approaching-limit warnings (`>= 85%`), and overall event budget warnings (80% and >100% threshold notifications) prevent fiscal surprises.
- **Dedicated Exporting**:
  - Generated dedicated CSV and PDF expense reports using ReportLab with executive summary metrics, category comparison tables, transaction ledgers, and savings/deficit analysis.
