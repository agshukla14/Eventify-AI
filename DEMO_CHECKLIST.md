# Eventify AI – Hackathon & Competition Demonstration Checklist
## 12-Step Comprehensive Live Demonstration Guide

Follow this 12-step sequence to deliver a flawless, high-impact demonstration showcasing full-stack capabilities, Gemini GenAI reasoning, external meteorological forecasting, and SaaS operations.

---

### Step 1: System Health & AI Gateway Verification
- **Action:** Open `http://localhost:8000/api/health` in browser or curl.
- **What to Highlight:**
  - Status returns `healthy`.
  - `gemini_configured: true` indicates live Google GenAI SDK connectivity with fallback repair engine.
  - `database: connected` verifies thread-safe relational persistence.

---

### Step 2: Executive Command Center Overview
- **Action:** Visit `http://localhost:5173/` and click the **Executive Dashboard** tab.
- **What to Highlight:**
  - SaaS command center with **8 Real-Time KPIs**: Total Events, Upcoming Events, Total Planned Budget, Total Actual Expenses, Remaining Budget, Confirmed Guests, Pending RSVPs, Booked Vendors.
  - Upcoming events countdown list with days-left countdown and budget spent progress bars.
  - Live Operational Activity Feed tracking recent expenses, guest RSVPs, and vendor contracts.
  - Interactive Recharts visual breakdown of Budget Allocation vs Spend and Guest RSVP attendance.

---

### Step 3: One-Click Event Intake & GenAI Plan Generation
- **Action:** Click **+ New Plan** in the top navbar.
- **Select Preset:** Click `💍 Royal Wedding` (or `🎂 Milestone Birthday` / `🎪 Community Festival`).
- **Submit:** Click **Generate AI Plan**.
- **What to Highlight:**
  - Gemini structured JSON output adheres to strict Pydantic schemas.
  - Guaranteed M1-M4 mathematical invariants (percentages sum to 100.0%, 5-10% contingency reserve, chronological milestone sequencing, mandatory vendor checklist coverage).

---

### Step 4: AI Smart Budget Optimizer
- **Action:** Click the **Budget Planner** tab.
- **Review:** Point out the **Budget Health** card, Highest Expense category, and High Savings Potential badges.
- **Optimize:** Click prompt chip `Reduce my wedding budget by ₹30,000` and click **Optimize Budget with AI**.
- **Apply:** Review side-by-side comparison, then click **Apply New Budget**. Show how budget amounts and percentages instantly update across the app.

---

### Step 5: Smart Expense Tracking & Budget Reconciliation
- **Action:** Click the **Expense Tracking** tab.
- **Add Expense:** Click **+ Add Expense**. Enter Expense Name: `Royal Heritage Catering Advance`, Category: `Catering`, Amount: `150000`, Status: `Paid`, Method: `Bank Transfer`. Click **Record Expense**.
- **What to Highlight:**
  - Actual Expenses KPI and Budget Utilized instantly reconcile.
  - Category and date filters, search bar, and **Export CSV** download.

---

### Step 6: Guest Management & RSVP Attendance Tracking
- **Action:** Click the **Guest Management** tab.
- **Add & Update:** Click **+ Add Guest**. Enter Name: `Vikramaditya Rathore`, Category: `VIP`, Plus-ones: `2`, Status: `Confirmed`.
- **CSV Bulk Import:** Click **Import CSV**. Paste sample CSV data (Name, Email, Category, Plus Ones). Show the live **Import Preview Table**, then click **Confirm Import**.
- **What to Highlight:**
  - Total Confirmed, Attending, and Pending badges update dynamically.
  - Filter by RSVP status and category, plus **Export Guest Roster (CSV)**.

---

### Step 7: Trilingual Cultural AI Invitation Generator
- **Action:** Click the **AI Invitations** tab.
- **Generate:** Select language **Hindi** (or **Gujarati** or **English**), Style **Traditional**, click **Generate AI Invitations**.
- **Customize & Style:** Select **Variation 2**, choose the **Royal Crimson & Gold** template, change border style to **Ornate Gold**.
- **What to Highlight:**
  - Live rendered card canvas preview with authentic cultural greetings and typography.
  - One-click **Copy Text**, **Download Card**, and **Share via WhatsApp** pre-populated messaging.

---

### Step 8: Curated Local Vendor Discovery & Comparison
- **Action:** Click the **Find Vendors** tab.
- **Filter & Search:** Filter by Category: `Photography`, Rating: `4.8+ Stars`.
- **Compare:** Select two top vendors (e.g., *LensCraft Royal Studios* and *ShutterVibes Jaipur*), click **Compare Selected Vendors (2)**.
- **Book:** Click **Book Vendor**, set agreed price ₹85,000, advance payment ₹25,000.
- **What to Highlight:**
  - Grounded comparison matrix displaying pros, cons, and budget recommendation.
  - Booking an advance payment automatically synchronizes with the Expense Tracking ledger!

---

### Step 9: AI Weather-Aware Radar & Mitigation Tasks
- **Action:** Click the **Weather & Event Planning** tab.
- **Inspect:** Point out the automatically fetched event location (`Jaipur`) and date. Click **Fetch Meteorological Intelligence**.
- **What to Highlight:**
  - Open-Meteo forward geocoding with coordinates.
  - Live 16-day forecast or 10-year historical climate reference badge.
  - Hourly temperature, precipitation probability, and wind speed charts.
  - Atmospheric Risk Assessment matrix (Heat Stress, Rain Probability, Wind Gusts).
  - Smart outdoor/indoor mitigations with one-click **Save Tasks to Timeline** (with duplicate prevention).

---

### Step 10: Grounded AI Assistant & Interactive Tool Calling
- **Action:** Click **Ask AI Assistant** in the header banner.
- **Prompt:** Type: `What is my remaining budget, and can you add a saxophone artist to the sangeet schedule?`
- **What to Highlight:**
  - Contextually grounded responses utilizing real budget numbers.
  - Tool calling executes schema updates to timeline run-of-show in real time.

---

### Step 11: Professional PDF & CSV Export Delivery
- **Action:** In the top navigation bar, click the **Export** dropdown and select **Download as PDF**.
- **What to Highlight:**
  - Generates a styled, multi-page ReportLab PDF report complete with event metadata, budget breakdown tables, milestone timelines, vendor checklists, and personalized ideas.
  - Also demo **Download as CSV** for spreadsheet workflows.

---

### Step 12: User Authentication & Multi-Event Management
- **Action:** Open `http://localhost:5173/` in a fresh browser session (or click **Sign Out** from the top navbar).
- **What to Highlight:**
  - Public marketing **Landing Page** with hero section, feature highlights, and interactive preview.
  - Dedicated SaaS **Sign In** (`/login`) and **Create Account** (`/register`) pages with real-time field validation.
  - PBKDF2-HMAC-SHA256 password hashing with 100,000 iterations and RFC 7519 JWT token issuance.
  - User-to-event isolation ensuring organizers only see their own celebration plans and sensitive expense data.
  - Navbar profile avatar shows user name and verified organizer badge with **Sign Out**.
