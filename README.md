# PRSentinel: Security Fix Regression Defense Engine & Dashboard

PRSentinel detects pull requests and commits that inadvertently or maliciously revert past security fixes. While conventional linters detect existing vulnerabilities, PRSentinel detects **regressions of resolved vulnerabilities** using deterministic line normalization, multi-signal scoring, and Git blame historical tracing.

The system operates as both a **standalone GitHub Action** in CI and as a full-featured **interactive Dashboard** with secure repo cloning, live telemetry, and rule management.

---

## Architecture

```mermaid
flowchart TD
    User["Security Engineer / Maintainer"] -->|HTTPS UI| Web["PRSentinel Web Dashboard (React + Tailwind)"]
    GHAction["GitHub Actions CI Workflow"] -->|Direct CLI| Engine["PRSentinel Detection Engine (prsentinel.py)"]

    Web -->|REST API| API["FastAPI Application Server"]

    subgraph Backend["Backend Architecture"]
        API --> Auth["Token & Role Auth"]
        API --> DB[(SQLAlchemy Database\nSQLite / PostgreSQL)]
        API --> JobRunner["In-Process Background Worker Queue"]
        JobRunner --> GitService["Secure Clone Sandbox\n(Hooks disabled, No-exec)"]
        JobRunner --> Scanner["Scanner Service"]
        Scanner --> Engine
        Scanner --> OSV["OSV API Integration\n(api.osv.dev)"]
    end

    GitService -->|git clone --| GitHub["GitHub Repositories / REST API"]
    Engine --> Findings["Risk Level & Breakdown\n🚨 HIGH / ⚠️ MEDIUM / ✅ LOW"]
    Findings --> DB
    Findings -->|Sticky Comment| PR["GitHub Pull Request"]
```

---

## Implemented vs Planned Capabilities

| Capability | Status | Implementation Details |
| :--- | :---: | :--- |
| **Deterministic Reversal Detection** | **Implemented** | Identifier-masked `difflib.SequenceMatcher` with literal and operator preservation. |
| **Trivial Line & Length Filters** | **Implemented** | Ignores normalized statements with `< 12` chars or `< 3` alphabetic tokens. |
| **Moved-Line / Refactor Protection**| **Implemented** | Checks if deleted validation lines were re-added elsewhere in PR; reduces score by 45 pts to eliminate false positives. |
| **Renamed & Deleted File Handling** | **Implemented** | Tracks `rename from/to` and `deleted file mode 100644` in unified diff parser. |
| **Secure Clone Service** | **Implemented** | Subprocess arg list (`shell=False`), URL after `--`, `core.hooksPath=/dev/null`, no submodules, timeout (120s), size check (250MB), auto temp cleanup. |
| **Credential Encryption & Redaction**| **Implemented** | Fernet token encryption at rest; regex sanitizers purge tokens and auth from all logs. |
| **Scan Modes (5 Modes)** | **Implemented** | `open_prs`, `single_pr`, `history_audit` (git blame on parent commits for CVE patterns), `branch_compare`, `patch_upload`. |
| **OSV API Fix Rule Import** | **Implemented** | Direct import from `https://api.osv.dev/v1/vulns/{id}` with commit diff preview. |
| **Interactive Test Workbench** | **Implemented** | Paste diff to preview deterministic score, breakdown, and sticky markdown comment. |
| **Accessible Dark UI Dashboard** | **Implemented** | React + Tailwind, 8px grid, Inter font, risk by icon + text (🚨 / ⚠️ / ✅), prefers-reduced-motion. |
| **Live Stepper & Log Streaming** | **Implemented** | Monospace auto-scrolling log console with per-job cancellation and error diagnostics. |
| **Audit Trail Logging** | **Implemented** | Immutable audit log table recording every repo add, rule update, and triage action. |
| **GitHub Action Independent CI** | **Implemented** | Stdlib-only backward compatible CLI entrypoint (`prsentinel.py`). |
| **GitHub App Marketplace Install** | *Planned* | Webhook-driven auto-installation across GitHub organizations. |
| **Enterprise SSO (SAML / OIDC)** | *Planned* | Identity federation with Okta, Azure AD, and Google Workspace. |
| **Slack / Email Threat Webhooks** | *Planned* | Instant notifications when HIGH severity regressions are detected. |
| **Tree-Sitter Semantic AST Analysis**| *Planned* | Full abstract syntax tree differential parsing for non-Python languages. |
| **Org-Wide Centralized Policy** | *Planned* | Organization-wide enforcement policies spanning multiple GitHub orgs. |

---

## Quickstart: Running Locally

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and npm
- Git

### 2. Backend Setup
```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run automated tests (pytest)
pytest tests -v

# Seed sample data (clearly labeled [SAMPLE DATA])
python -m backend.seed

# Start FastAPI server (serves API and compiled UI)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Frontend Development (Hot Reload)
```bash
cd frontend
npm install
npm run dev
# Vite dev server runs at http://localhost:3000 (proxies /api to :8000)
```

To build production static assets:
```bash
cd frontend
npm run build
```

---

## Running with Docker

Build and run the complete self-contained container (non-root user, Git installed):

```bash
docker-compose up --build
```

Access the dashboard at **`http://localhost:8000`**.

---

## Deployment Steps

### Backend Deployment (Render / Railway / Fly.io)

1. **Deploy as Docker Container or Python Web Service**:
   - Build Command: `pip install -r requirements.txt && cd frontend && npm install && npm run build && cd ..`
   - Start Command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
2. **Environment Variables**:
   - `DATABASE_URL`: Set to PostgreSQL URI (e.g. Supabase / Neon `postgresql://user:pass@host:5432/db`) or default SQLite.
   - `ADMIN_PASSWORD`: Administrator password for dashboard access.
   - `ADMIN_TOKEN`: API bearer secret.
   - `ENCRYPTION_SECRET`: 32-byte Fernet base64 key for encrypting private repository tokens at rest.
   - `GITHUB_TOKEN`: (Optional) GitHub Personal Access Token to avoid unauthenticated API rate limits.
   - `MAX_CLONE_TIMEOUT_SEC`: `120`
   - `MAX_REPO_SIZE_MB`: `250`
   - `MAX_CONCURRENT_JOBS`: `2`

### Frontend Deployment (Vercel)

If decoupling the frontend from the FastAPI server:
1. Set Root Directory to `frontend`.
2. Framework Preset: `Vite`.
3. Build Command: `npm run build`.
4. Output Directory: `dist`.
5. Configure Rewrites in `vercel.json`:
   ```json
   {
     "rewrites": [{ "source": "/api/(.*)", "destination": "https://your-backend.onrender.com/api/$1" }]
   }
   ```

### Database Deployment (Supabase / Neon)
1. Provision a PostgreSQL instance.
2. Copy the Connection String: `postgresql://postgres:[PASSWORD]@[HOST]:5432/postgres`.
3. Set `DATABASE_URL` in backend environment variables. SQLAlchemy will automatically create all tables on first startup.

---

## Verification & Test Results

Run the full pytest suite:
```bash
pytest tests -v
```

Tests cover:
- URL validation (rejecting `file://`, `ssh://`, option injection `--upload-pack`, non-GitHub hosts)
- Safe clone argument lists passed after `"--"` with hooks disabled
- Token scrubbing from logs and git remote configuration
- History audit detecting planted regressions in Git repositories via `git blame`
- Moved-line refactoring detection reducing scores
- XSS payload sanitization on repo-derived commit messages and titles
- Full API endpoint CRUD and simulation checks
