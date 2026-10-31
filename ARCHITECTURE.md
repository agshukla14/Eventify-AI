# ARCHITECTURE.md: Celebration & Event Planner Assistant

An autonomous, full-stack GenAI planning platform engineered with deterministic post-processing repair layers, structured Gemini JSON outputs, SQLite persistence, and an interactive React frontend.

---

## 1. High-Level Architecture Diagram

```mermaid
graph TD
    subgraph Client ["Frontend (React 18 + Vite + TypeScript + Tailwind)"]
        UI[User Interface & Dashboard]
        IntakeUI[Event Intake Wizard & Presets]
        BudgetUI[Interactive Budget Planner & Charts]
        TimelineUI[Adaptive Milestone & Run-of-Show]
        VendorUI[Vendor Checklist & Contract Tracker]
        IdeasUI[Personalized Ideas & Swaps]
        ChatDrawer[AI Assistant Grounded Chat]
    end

    subgraph API ["Backend (FastAPI + Python 3.11)"]
        Router[FastAPI Application Router]
        PlanSvc[Plan Service]
        ChatSvc[Chat & Tool Service]
        ExportSvc[Export Service ReportLab / CSV]
    end

    subgraph GenAI ["GenAI & Generation Pipeline"]
        GeminiClient[Google Gemini API gemini-2.5-flash]
        RetryLoop[Retry Loop with Error Feedback max 3x]
        FallbackEngine[Deterministic Template Engine Offline Mode]
    end

    subgraph Guardrails ["Deterministic Repair & Guard Engine"]
        Normalizer[Budget Normalizer 100% exact & Contingency]
        TimelineClamper[Timeline Clamper & Sprint Compressor]
        VendorInjector[Mandatory Vendor Coverage & Checklists]
        DietGuard[Dietary & Age Constraint Guard]
    end

    subgraph Persistence ["Storage"]
        SQLite[(SQLite celebration_planner.db)]
    end

    UI -->|HTTP / JSON / REST| Router
    Router --> PlanSvc
    Router --> ChatSvc
    Router --> ExportSvc

    PlanSvc --> GeminiClient
    GeminiClient -->|Validation Error| RetryLoop
    RetryLoop -->|On Exhaustion| FallbackEngine

    GeminiClient --> Guardrails
    FallbackEngine --> Guardrails

    Guardrails --> Normalizer
    Guardrails --> TimelineClamper
    Guardrails --> VendorInjector
    Guardrails --> DietGuard

    Guardrails -->|Guaranteed Invariants| PlanSvc
    ChatSvc --> Guardrails
    PlanSvc --> SQLite
    ChatSvc --> SQLite
```

---

## 2. Core Subsystems

### A. Intake & Invariant Validation (`EventIntake`)
- Captures event type (`wedding`, `birthday`, `community`), target date, city, guest count, total budget, currency, theme, cultural traditions, dietary constraints, must-haves, and age group details.
- Validated via Pydantic v2 schemas.

### B. GenAI Integration & Retry Loop (`GeminiClient`)
- Communicates with Google Gemini API (`gemini-2.5-flash`) via `google-genai`.
- Enforces structured JSON output matching domain schemas.
- If JSON decoding or Pydantic validation fails, feeds the exact error back to Gemini in a retry prompt (up to 3 attempts).
- Automatically routes to `FallbackTemplateEngine` if offline, without API key, or upon retry exhaustion.

### C. Deterministic Post-Processing & Repair Engine (`DeterministicRepairEngine`)
- **Budget Normalization**: Guarantees that percentages sum to 100.00% and amounts sum to the exact total budget down to the penny. Enforces a 5-10% contingency reserve.
- **Timeline Clamping & Compression**: Clamps dates between `today` and `event_date`. If lead time is < 30 days, activates a compressed sprint schedule and flags critical bookings as high-risk. Generates a day-of hourly run-of-show.
- **Mandatory Vendor Injection**: Guarantees 100% mandatory categories are present for the event type with >= 4 checklist verification items each.
- **Dietary & Age Guard**: Cleanses food items violating vegetarian, Jain, or vegan constraints; cleanses alcoholic items from kids parties.

### D. Grounded AI Chat Assistant & Tool Calling (`ChatService`)
- Grounded in active plan data to answer questions about budget status, days left, vendor bookings, and timelines.
- Dispatches tool actions:
  - `move_budget(from_cat, to_cat, amount_or_percent)`
  - `adjust_event_date(new_date)`
  - `update_vendor_status(category, status)`
  - `update_task_status(task_id, status)`
  - `add_custom_task(title, date)`
  - `add_personalized_idea(category, title)`
- Every tool call executes through the repair engine, keeping the plan 100% consistent.

### E. Persistence & Export Engine (`ExportService`)
- SQLite storage via SQLAlchemy (`EventModel`, `ChatMessageModel`).
- PDF generation using ReportLab with custom tables and typography.
- Multi-section CSV export for spreadsheets.

---

## 3. Data Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant Frontend as React Frontend
    participant API as FastAPI Backend
    participant Gemini as Gemini API
    participant Guard as Deterministic Repair
    participant DB as SQLite Database

    User->>Frontend: Enters Intake Form / Chooses Preset
    Frontend->>API: POST /api/events
    API->>Gemini: generate_content(schema, prompt)
    alt Gemini Success
        Gemini-->>API: Raw JSON plan
    else Timeout / No Key
        API->>API: FallbackTemplateEngine
    end
    API->>Guard: repair_full_plan(raw_plan, intake)
    Guard-->>API: Guaranteed Invariants Plan
    API->>DB: Save Event & Plan JSON
    API-->>Frontend: FullEventPlan
    Frontend-->>User: Displays Dashboard, Charts, Vendors, Timeline
    User->>Frontend: Chat: "Move 5000 from Decor to Catering"
    Frontend->>API: POST /api/chat
    API->>Guard: Execute move_budget & normalize
    Guard-->>API: Rebalanced Plan
    API->>DB: Save updated plan & chat message
    API-->>Frontend: ChatResponse + updated_plan
    Frontend-->>User: Instant live chart update
```
