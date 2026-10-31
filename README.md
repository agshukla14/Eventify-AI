# Celebration & Event Planner (GenAI Assistant)

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61dafb.svg)](https://react.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-3.4-38bdf8.svg)](https://tailwindcss.com/)
[![Accuracy](https://img.shields.io/badge/Eval_Accuracy-100%25-brightgreen.svg)](#evaluation-results)

A production-grade, GenAI-powered Celebration & Event Planning Assistant built for **Weddings**, **Birthdays**, and **Community Events**. The system integrates **Google Gemini GenAI** with a **deterministic post-processing and repair layer** that guarantees strict mathematical and temporal invariants: percentages sum to exactly 100%, amounts match total budget, mandatory categories are covered, and dates adapt dynamically to lead times.

---

## 🌟 Key Features

1. **Smart Intake Wizard**:
   - Tailored intakes for **Weddings**, **Birthdays**, and **Community Events**.
   - Input fields: Date, City, Guest Count, Total Budget (INR default, multi-currency), Theme/Style, Cultural Traditions, Dietary Constraints, Must-Haves, and Age Group.
   - **One-Click Demo Presets** to test complete plans instantly.

2. **Deterministic Budget Planner**:
   - Category allocations customized to event type (Venue, Catering, Decor, Photography, Entertainment, Logistics/Permits, Contingency).
   - **Strict Math Guarantee**: Code normalizes allocations so percentages sum to **exactly 100.00%** and amounts match total budget to the penny.
   - **5-10% Contingency Reserve** always safeguarded.
   - Live interactive Recharts charts (distribution pie chart & allocated vs actual spend bar chart).
   - In-app fund transfers between categories with instant re-balancing.

3. **Adaptive Milestone Timeline & Run-of-Show**:
   - Milestone schedule counting backwards from the event date.
   - **Adaptive Compression**: If the event is < 30 days away, activates a compressed sprint schedule and flags critical vendor booking tasks as `HIGH RISK`.
   - All dates ordered chronologically, validated, and clamped to `today <= due_date <= event_date`.
   - Complete day-of hourly run-of-show schedule.

4. **Mandatory Vendor Checklist**:
   - 100% coverage guarantee for mandatory categories by event type.
   - Each category contains at least 4 verification checklist tasks (contract verification, deposit due date, interview questions, balance payment date).
   - Pre-screened backup vendor contingency options.

5. **Personalized Ideas & Budget Swaps**:
   - Creative ideas across Themes, Decor, Food & Catering, Activities, Entertainment, and Return Gifts.
   - References user inputs (city, culture, theme, guest count, age group).
   - **Dietary & Age Guard**: Automatically filters out meat for vegetarians/vegans/Jains, and excludes alcohol for kids parties.
   - Every single idea comes with an actionable **budget-friendly swap**.

6. **Context-Aware Grounded AI Assistant**:
   - Slide-out chat drawer grounded in the active plan data.
   - Answers questions ("How many days left?", "What is my catering budget?", "Who is booked for photography?").
   - Executes plan modifications via conversational commands ("move 5000 from Decor to Catering", "mark photography as booked", "change event date to 2027-01-20") with automatic post-validation.

7. **Persistence & Export**:
   - Persistent SQLite database storing multiple events and chat history.
   - One-click export to **PDF** (via ReportLab with formatted tables) and structured **CSV**.

8. **Zero-Crash Resilience**:
   - If `GEMINI_API_KEY` is not provided, times out, or quota is exhausted, the app seamlessly runs on `FallbackTemplateEngine` without crashing or returning 500.

---

## 🚀 Quick Start (One-Command Run)

### Prerequisites
- Python 3.11+
- Node.js 18+ and npm

### 1. Setup & Environment
```bash
# Clone the repository
git clone <repo-url>
cd "GenAI Project"

# Configure environment (Optional: add your Gemini API Key)
cp .env.example .env
```

### 2. Start Both Servers (One Command)
Run any of the following equivalents:

```bash
# Option A: Make dev
make dev

# Option B: Cross-platform Python starter
python start_app.py

# Option C: Windows batch file
.\run_dev.bat
```

Open your browser to:
👉 **http://localhost:8000** (Serves both the React frontend and FastAPI backend)

---

## ⏱️ 2-Minute Demo Script

Follow these steps to experience the complete flow:

1. **Open the App**:
   - Navigate to `http://localhost:8000`.
   - The pre-seeded **"Priya & Rohan Royal Heritage Wedding"** in Jaipur loads instantly.
   - Review the **Dashboard Overview**: Days Remaining, Budget Utilized %, Tasks Completed %, and Vendors Booked.

2. **Explore Budget Planner**:
   - Click the **"Budget Planner"** tab.
   - Notice the category distribution pie chart and the allocated vs actual spend comparison bar chart.
   - Notice the **Contingency Reserve (8.00%)** and total allocation sum of exactly 100.00%.
   - Click **"Reallocate Category Funds"**, transfer 10,000 INR from Decor to Catering, and see the amounts instantly update with zero math errors.

3. **Explore Adaptive Timeline**:
   - Click the **"Timeline & Schedule"** tab.
   - Review the chronological milestones leading up to the wedding date.
   - Toggle task checkboxes to mark them completed and watch the completion percentage update.
   - Scroll down to review the **Day-of Hourly Run-of-Show** schedule.

4. **Verify Mandatory Vendor Checklist**:
   - Click the **"Vendor Checklist"** tab.
   - Observe that all mandatory categories (Venue, Catering, Photography, Decor, Music) are present.
   - Click on **"Photography & Video"** and check off the contract verification task.
   - Change booking status to **"Booked"**.

5. **Review Personalized Ideas & Swaps**:
   - Click the **"Personalized Ideas"** tab.
   - Notice the curated themes, decor, food, activities, and gifts highlighting Jaipur and Marwari traditions.
   - Notice the **"Diet Guard Active"** badge ensuring 0 meat items in the food menu.
   - Review the green **Budget-Friendly Swap** callout on each card.

6. **Chat with AI Assistant & Execute Tools**:
   - Click the **"AI Assistant"** button in the header or the banner.
   - Click the prompt chip: *"Move 5,000 from Decor to Catering"*.
   - Watch the assistant execute the tool and rebalance the plan state in real time.
   - Ask: *"What is my catering budget?"* and observe the grounded answer.

7. **Export Plan**:
   - Click the **"Export"** dropdown in the navbar.
   - Click **"Download as PDF"** to receive a formatted PDF document.
   - Click **"Download as CSV"** to receive the structured spreadsheet.

8. **Test a New Celebration with Presets**:
   - Click **"New Plan"** in the top bar.
   - Click **"🎂 10th Birthday"** or **"🎪 Community Mela"** to autofill the form.
   - Click **"Generate AI Plan"** to watch the full generator create a new celebration plan.

---

## 📊 Evaluation & Verification

The project includes an automated evaluation runner testing **42 diverse scenarios** (14 Weddings, 14 Birthdays, 14 Community Events) with varying budgets (INR 0 to 5,000,000+), lead times (7 days to 18 months), guest counts (10 to 1,000), and edge cases (adversarial prompt injections, rush dates, tiny budgets).

### Run Evals:
```bash
python evals/run_evals.py
```

### Metrics Scorecard:
| Metric | Name | Accuracy Score | Target | Status |
|---|---|---|---|---|
| **M1** | Budget Integrity | **100.0%** (42/42) | >= 95% | ✅ PASS |
| **M2** | Timeline Validity | **100.0%** (42/42) | >= 95% | ✅ PASS |
| **M3** | Vendor Coverage | **100.0%** (42/42) | >= 95% | ✅ PASS |
| **M4** | Idea Personalization & Constraints | **100.0%** (42/42) | >= 95% | ✅ PASS |
| **M5** | Schema Validity | **100.0%** (42/42) | >= 95% | ✅ PASS |
| **M6** | Chat / Tool Correctness | **100.0%** (22/22) | >= 95% | ✅ PASS |
| **M7** | Robustness & Edge Handling | **100.0%** (42/42) | >= 95% | ✅ PASS |
| **M8** | API & Playwright Smoke Tests | **100.0%** (8/8) | >= 95% | ✅ PASS |

Full detailed metrics and analysis are recorded in [EVAL_REPORT.md](file:///d:/GenAI%20Project/EVAL_REPORT.md).

---

## 🧪 Testing

Run unit tests, integration tests, and Playwright smoke tests:
```bash
pytest backend/tests
```

---

## 🛠️ Tech Stack & Architecture

- **Backend**: Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, SQLite, ReportLab, Pytest, Playwright.
- **Frontend**: React 18, Vite, TypeScript, Tailwind CSS, Lucide Icons, Recharts.
- **GenAI**: Google Gemini API (`gemini-2.5-flash`) with structured JSON schema outputs, 3x error feedback retry loop, and offline deterministic fallback template engine.

For architectural diagrams and component specifications, see [ARCHITECTURE.md](file:///d:/GenAI%20Project/ARCHITECTURE.md) and [DECISIONS.md](file:///d:/GenAI%20Project/DECISIONS.md).
