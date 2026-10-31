# Eventify AI – Production Deployment Guide
## Deploying to Render with PostgreSQL & Google Gemini API

This document provides complete instructions for deploying the **Eventify AI Celebration & Event Planner** application to [Render](https://render.com).

---

### 1. Architecture Overview
- **Unified Single-Service Model:**
  - Build step compiles the React 18 / Vite frontend into `frontend/dist`.
  - FastAPI serves both the REST API `/api/*` and the compiled single-page application at the root `/`.
- **Database:**
  - Local development uses SQLite (`DATABASE_URL=sqlite:///./celebration_planner.db`).
  - Production uses Render Managed PostgreSQL (`DATABASE_URL=postgresql://...`).
  - Legacy `postgres://` connection strings are automatically rewritten to `postgresql://` by the database engine.
- **AI Engine:**
  - Google Gemini 2.5 Flash with structured schema validation and multi-turn retry repair engine.
- **Authentication:**
  - Standard RFC 7519 JWT (HS256) with PBKDF2-HMAC-SHA256 password hashing.

---

### 2. Method A: One-Click Render Blueprint Deployment (Recommended)
1. Push this repository to GitHub or GitLab.
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** and select **Blueprint**.
3. Connect your repository. Render will automatically detect `render.yaml`.
4. Configure the following environment variables:
   - `GEMINI_API_KEY`: Your Google Gemini API key from Google AI Studio.
5. Click **Apply**.
   Render will automatically:
   - Provision an `eventify-db` PostgreSQL instance.
   - Run `npm --prefix frontend install && npm --prefix frontend run build && pip install -r backend/requirements.txt`.
   - Apply production database migrations via `alembic upgrade head`.
   - Start the service with `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`.

---

### 3. Method B: Manual Web Service Setup on Render
If not using Blueprints:
1. **Create Managed Database:**
   - In Render Dashboard: **New +** -> **PostgreSQL**.
   - Name: `eventify-db`.
   - Region: `Oregon` (or region of your choice; must match web service).
   - Copy the **Internal Database URL**.
2. **Create Web Service:**
   - In Render Dashboard: **New +** -> **Web Service**.
   - Connect repository.
   - Environment: `Python 3`.
   - Region: Same as database (e.g. `Oregon`).
   - Branch: `master` or `main`.
   - Health Check Path: `/api/health`.
   - Build Command:
     ```bash
     npm --prefix frontend install && npm --prefix frontend run build && pip install -r backend/requirements.txt
     ```
   - Start Command:
     ```bash
     alembic upgrade head && uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
     ```
3. **Environment Variables:**
   | Variable | Value | Description |
   | :--- | :--- | :--- |
   | `PYTHON_VERSION` | `3.11.9` | Required Python runtime |
   | `APP_ENV` | `production` | Production mode |
   | `DATABASE_URL` | `<Internal Database URL>` | Render PostgreSQL connection string |
   | `GEMINI_API_KEY` | `<Your Key>` | Google Gemini API key |
   | `JWT_SECRET` | `<Random 32-char string>` | Secret key for signing auth tokens |
   | `DEFAULT_CURRENCY`| `INR` | Default celebration currency |

---

### 4. Verification & Post-Deployment Health Check
Once deployed, verify your live URL:
1. **API Health Check:**
   ```bash
   curl -s https://<your-render-url>.onrender.com/api/health
   ```
   Expected response:
   ```json
   {"status":"healthy","gemini_configured":true,"database":"connected"}
   ```
2. **Executive Command Center:**
   Visit `https://<your-render-url>.onrender.com/` in your browser.
   - Verify the 8 Executive KPI metrics load.
   - Verify the demo wedding plan is available or create a new event.
   - Test PDF and CSV exports.
   - Test AI Invitation generation, Vendor booking, and Weather Planning.
