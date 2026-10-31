# PLAN: Celebration & Event Planner (GenAI Assistant)

## 1. Executive Summary
An autonomous, production-grade GenAI Celebration & Event Planner supporting Weddings, Birthdays, and Community Events. The system guarantees strict deterministic guarantees on arithmetic, dates, mandatory coverage, and safety, coupled with rich Gemini-driven personalization and an interactive tool-calling AI assistant.

---

## 2. System Architecture

```
[ Frontend: React + Vite + TypeScript + TailwindCSS + Lucide + Recharts ]
                            │  HTTP / REST / JSON
                            ▼
[ Backend: FastAPI (Python 3.11) + SQLAlchemy + SQLite ]
       │
       ├── Intake & Validation Engine (Pydantic v2)
       ├── Deterministic Math & Repair Engine (Normalizer, Date Clamper, Constraint Guard)
       ├── Gemini GenAI Client (Structured Outputs + 3x Error-Feedback Retries)
       │     └── Offline Deterministic Fallback Template Engine
       ├── Plan Services:
       │     ├── Budget Planner (Tailored categories, 5-10% contingency, exact sums)
       │     ├── Timeline & Run-of-Show (Adaptive milestones, date math, risk flags)
       │     ├── Vendor Checklist (Mandatory coverage, >=4 items, quotes, deposit dates)
       │     ├── Personalized Ideas (Themes, food, decor, activities + budget swaps)
       │     └── AI Chat Assistant (Function calling / tools + live re-validation)
       └── Export Engine (PDF via ReportLab + CSV)
```

---

## 3. Pydantic Schemas & Domain Models

### Event Intake
- `event_type`: `wedding` | `birthday` | `community`
- `title`: string
- `date`: `YYYY-MM-DD` (validated against future / adaptive thresholds)
- `city`: string
- `guest_count`: int (positive)
- `total_budget`: float (positive)
- `currency`: string (default: "INR", supports "USD", "EUR", "GBP", etc.)
- `theme_style`: string (optional)
- `cultural_preferences`: string (optional)
- `dietary_preferences`: list[str] (e.g. Vegetarian, Vegan, Halal, Jain, Nut-free)
- `must_haves`: list[str]
- `age_group_details`: string (optional, e.g. "Kids 5-10", "Adults 30s", "All ages")

### Budget Category
- `category`: string (Venue, Catering, Decor, Photography, Entertainment, Attire, Invitations, Logistics/Permits, Contingency, etc.)
- `percentage`: float (sum to exactly 100.0)
- `allocated_amount`: float (sum to exactly total_budget)
- `actual_spent`: float (default: 0.0)
- `notes`: string

### Timeline & Day-of Schedule
- Milestone Task: `id`, `milestone_phase` (e.g., "12 Months Before", "3 Weeks Before"), `title`, `description`, `due_date`, `owner` (user | vendor | helper), `priority` (high | medium | low), `status` (pending | in_progress | completed), `is_high_risk` (bool), `is_past_due` (bool).
- Run of Show: `time_slot`, `activity`, `lead_person`, `location`, `notes`.

### Vendor Category & Checklist
- Category name (e.g. Catering, Venue, Photography, Sound & Lighting)
- Mandatory flag
- Items: list of >= 4 items per category (questions to ask, contracts/permits, deposit date, final payment date, backup vendor name/contact).
- Vendor details: `vendor_name`, `contact_info`, `quote_amount`, `status` (`not_contacted` | `quoted` | `booked` | `paid`), `linked_budget_category`.

### Personalized Ideas
- Categories: Themes, Decor, Food & Catering, Activities & Games, Entertainment, Return Gifts/Favors.
- Each idea item: `title`, `description`, `rationale` (links to culture, city, age, theme), `budget_friendly_swap`, `tags` (diet, age-appropriate, etc.).

---

## 4. Deterministic Post-Processing & Repair Layer (Anti-Cheat & Reliability)

Regardless of LLM response or failure:
1. **Budget Repair**:
   - Ensures mandatory contingency (default 8% or clamped 5-10%).
   - Normalizes all percentages so `sum(percentages) == 100.00%`.
   - Normalizes currency allocations so `sum(allocated_amount) == total_budget` to the exact cent.
2. **Timeline Repair**:
   - Computes real calendar dates backwards from `event_date`.
   - Clamps any date so `today <= due_date <= event_date`.
   - If lead time is short (e.g., < 30 days), dynamically compresses milestones and sets `is_high_risk = True` on critical booking tasks.
   - Guarantees sorted chronological order and full day-of hourly run-of-show.
3. **Vendor Coverage Repair**:
   - Injects any missing mandatory vendor category for the event type.
   - Enforces minimum 4 checklist items per category (including contract, deposit, final payment, and backup).
4. **Constraint & Diet Guard**:
   - Inspects food items against dietary constraints (e.g., removes meat if vegetarian/vegan/Jain, flags alcohol for children's parties).
   - Injects appropriate alternatives if LLM hallucinated prohibited items.

---

## 5. GenAI Prompt & Retry Strategy
1. **Model**: `gemini-2.5-flash` or `gemini-1.5-flash` via `google-genai` / `google-generativeai`.
2. **Structured JSON**: Enforce `response_mime_type="application/json"` with schema definition.
3. **Retry with Feedback**: If Pydantic validation fails, feed the validation error string back into a retry prompt (up to 3 attempts).
4. **Offline / Fallback Deterministic Engine**: If `GEMINI_API_KEY` is not provided, expired, or rate-limited, immediately fall back to a rich deterministic generator producing high-quality personalized plans. The application **never crashes or returns 500**.

---

## 6. AI Chat & Tool System
- Chat endpoint grounded in event plan state.
- Tool Calling capabilities:
  1. `move_budget(from_category, to_category, amount_or_percent)`
  2. `adjust_event_date(new_date)` (recalculates timeline)
  3. `add_or_update_task(task_id_or_title, ...)`
  4. `update_vendor_status(category, vendor_name, quote, status)`
  5. `regenerate_ideas(category_filter, specific_request)`
- Every tool action runs through the deterministic repair and re-validation layer.

---

## 7. Eval Design (Accuracy Contract: >= 95% on M1 - M8)
- Test suite with 42 scenarios across:
  - 14 Weddings (budget 200,000 INR to 5,000,000 INR; 2 weeks to 14 months lead time; various Indian & global cultural preferences; various diets).
  - 14 Birthdays (1st birthday, sweet 16, 30th, 50th, 80th; small house party to luxury banquet; theme constraints).
  - 14 Community Events (charity gala, cultural festival, hackathon, sports day, block party; permits/insurance mandatory; 100 to 1000 guests).
  - Edge cases: tiny budget, huge guest count, 1-week lead time, prompt injection attempts in text fields.
- Metrics evaluated:
  - **M1 Budget Integrity**: exact 100% sum, exact total sum, no negatives, contingency 5-10%, mandatory categories.
  - **M2 Timeline Validity**: valid chronological dates, lead-time adaptation, day-of run-of-show.
  - **M3 Vendor Coverage**: 100% mandatory categories, >=4 items each, contract/deposit dates present.
  - **M4 Personalization & Constraint Adherence**: references user inputs, 0 diet/safety violations.
  - **M5 Schema Validity**: 100% Pydantic validation rate without uncaught exceptions.
  - **M6 Chat / Tool Correctness**: >=20 scripted tool commands with state matching.
  - **M7 Robustness**: edge cases return valid plans or graceful handled errors, zero 500s.
  - **M8 API & UI Tests**: 100% pytest pass rate, Playwright end-to-end smoke test passes.

---

## 8. Implementation Steps & The Loop
1. Setup virtualenv, backend dependencies (`fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `google-genai`, `reportlab`, `pytest`, `pytest-asyncio`, `httpx`).
2. Implement backend schemas, domain models, deterministic math & repair engine.
3. Implement Gemini LLM client + retry loop + fallback template engine.
4. Implement Plan Services (Budget, Timeline, Vendors, Ideas, Chat Tools, Export PDF/CSV).
5. Implement FastAPI endpoints and SQLite persistence.
6. Build Evals dataset (42 scenarios) and runner `evals/run_evals.py`.
7. Setup React frontend with Vite, Tailwind CSS, Lucide, Recharts, and build complete UI.
8. Run eval loop: BUILD -> EVALUATE -> FIX -> RE-EVALUATE until all metrics >= 95% for 2 consecutive runs. Write `EVAL_REPORT.md`.
9. Document `DECISIONS.md`, `ARCHITECTURE.md`, `README.md`, `.env.example`, and seed data.
