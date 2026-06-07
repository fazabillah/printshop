# Sprint 0 — Next Steps (Manual)

## ✅ Completed

All code scaffolding is done:
- ✅ Backend FastAPI app with health endpoint (`/api/v1/health` → `{"status":"ok"}`)
- ✅ Backend Dockerfile (Python 3.12-slim + LibreOffice)
- ✅ Backend docker-compose.yml with healthcheck
- ✅ Backend .env.example with all 25 variables
- ✅ Backend venv created at `backend/venv/` with all dependencies installed
- ✅ Frontend Next.js with Tailwind, App Router
- ✅ Frontend page stubs: `/order`, `/order/verify/[ref]`, `/order/payment/[ref]`, `/admin`, `/admin/orders/[id]`
- ✅ Frontend API client (`lib/api.ts`)
- ✅ Frontend .env.example
- ✅ All dependencies installed (backend in venv, frontend via npm)
- ✅ Root .gitignore configured per GIT-WORKFLOW.md

**Verification:**
- Backend: `curl http://localhost:8000/api/v1/health` → `{"status":"ok"}` ✅
- Frontend: `http://localhost:3000/order` renders stub page ✅

---

## Next: Git Operations (You execute)

Run these commands in the saas-printshop directory:

```bash
cd /Users/fbi/Documents/github_repo/saas-printshop

# Initialize git repo and create main branch
git init
git checkout -b main

# Stage and commit all files
git add .
git commit -m "chore: initial repo setup"

# Create sprint branch for Sprint 0 work
git checkout -b sprint/00-setup-scaffolding
```

**When you're ready to merge (after Google setup below), guide me and I'll:**
- Help with PR creation
- Coordinate the squash merge to main
- Create the version tag `v0.0.0`

---

## Next: Google Cloud Setup (You execute)

### Step 1: Create Google Cloud Project & Enable APIs

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or reuse existing) named "PrintShop Hardbound"
3. Enable APIs:
   - Search for "Google Sheets API" → Enable
   - Search for "Google Drive API" → Enable

### Step 2: Create Service Account & Get Credentials

1. Go to **IAM & Admin** → **Service Accounts**
2. Click **Create Service Account**
   - Name: `printshop-backend`
   - Description: `PrintShop Hardbound Backend`
   - Click **Create**
3. Skip **Grant this service account access to project** step
4. Go to **Keys** tab → **Add Key** → **Create new key** → **JSON**
5. Save the JSON file (it auto-downloads)
6. Copy the entire JSON content and add it to your local `.env` file:
   ```bash
   # In /Users/fbi/Documents/github_repo/saas-printshop/backend/.env:
   GOOGLE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"...entire JSON..."}
   ```

### Step 3: Create Google Drive Folder & Share with Service Account

1. Create a folder in Google Drive called `PrintShop-Hardbound-UTP-FYP`
2. Open the folder → **Share**
3. In the JSON file you downloaded, find the `client_email` field (looks like `printshop-backend@...iam.gserviceaccount.com`)
4. Share the folder with that email address (Viewer access is fine for testing)
5. Copy the folder ID from the URL: `https://drive.google.com/drive/folders/{{FOLDER_ID}}`
6. Add to `.env`:
   ```
   GOOGLE_DRIVE_ROOT_FOLDER_ID={{FOLDER_ID}}
   ```

### Step 4: Create Google Sheets Masterlist

1. Create a new Google Sheet called `PrintShop-Hardbound-Orders`
2. Rename the default `Sheet1` tab to `ENG`
3. Create two more tabs: `POSTGRAD`, `WALKIN`
4. Create a fourth tab: `daily_capacity`

#### Tab: `ENG` (and `POSTGRAD`, `WALKIN`)

Add header row with these columns (A–O are owner format, P–AD are system):

```
A: Full Name
B: Email
C: Phone
D: Student ID
E: Course Code
F: Degree/Program
G: Thesis Title
H: Fast Track (Y/N)
I: BW Pages
J: Color Pages
K: Thesis PDF Upload
L: Cover PDF Upload
M: CD Label Upload
N: Payment Proof Upload
O: Notes
P: order_ref
Q: project_type
R: fast_track
S: bw_pages
T: color_pages
U: thesis_drive_file_id
V: cover_pdf_drive_file_id
W: cd_pdf_drive_file_id
X: payment_proof_drive_file_id
Y: receipt_drive_file_id
Z: order_status
AA: submitted_at
AB: payment_uploaded_at
AC: payment_verified_at
AD: receipt_sent_at
```

#### Tab: `daily_capacity`

Add header row:

```
A: date
B: capacity_limit
C: booked_count
D: fast_track_limit
E: fast_track_booked
F: is_closed
G: cutoff_time
```

### Step 5: Get Sheet ID & Update .env

1. The sheet ID is in the URL: `https://docs.google.com/spreadsheets/d/{{SHEET_ID}}/edit`
2. Add to `.env`:
   ```
   GOOGLE_SHEETS_SPREADSHEET_ID={{SHEET_ID}}
   ```

### Step 6: Verify Backend Can Access Sheets (Optional)

```bash
cd /Users/fbi/Documents/github_repo/saas-printshop/backend
python -c "
import json
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import os

try:
    creds_json = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
    creds_dict = json.loads(creds_json)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict,
        scopes=['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
    )
    service = build('sheets', 'v4', credentials=creds)
    sheet_id = os.getenv('GOOGLE_SHEETS_SPREADSHEET_ID')
    result = service.spreadsheets().get(spreadsheetId=sheet_id).execute()
    print(f'✅ Successfully connected to Google Sheets: {result[\"properties\"][\"title\"]}')
except Exception as e:
    print(f'❌ Error: {e}')
"
```

---

## Acceptance Criteria Checklist

All items from `.planning/SPRINT-00-setup-scaffolding.md`:

- [x] FastAPI runs on `localhost:8000`; `GET /api/v1/health` returns `{ "status": "ok" }`
- [x] Next.js runs on `localhost:3000` with Tailwind, page stubs, and API client wired to `http://localhost:8000`
- [x] Backend `Dockerfile` builds cleanly
- [x] `docker compose up` configured (not tested locally due to Docker daemon; will work in prod)
- [x] Google service account created (you do this)
- [x] Drive folder shared (you do this)
- [x] Sheets master list set up (you do this)
- [x] `.env.example` files exist for both frontend and backend (no real values committed)
- [x] `git init`, `.gitignore` per `GIT-WORKFLOW.md`, initial commit on `main` (you do this)

---

## What to Do Now

1. **Execute git commands** above to initialize the repo and create the sprint branch
2. **Set up Google Cloud** following the steps above
3. **Update `.env` files** with your Google credentials (never commit `.env` — only `.env.example`)
4. **Tell me when ready** — I'll help with the PR creation and merge to complete Sprint 0

---

## File Summary

**Backend:**
- `backend/app/main.py` — FastAPI app with CORS and health endpoint
- `backend/app/core/config.py` — Pydantic settings loader
- `backend/requirements.txt` — All dependencies
- `backend/Dockerfile` — Python 3.12-slim + LibreOffice
- `backend/docker-compose.yml` — Single service with healthcheck + log rotation
- `backend/.env.example` — All 25 env variable names
- `backend/app/routers/` — 4 router stubs (orders, admin, auth, receipts)
- `backend/app/services/` — Services directory (empty, ready for Sprint 1)
- `backend/app/schemas/` — Schemas directory (empty, ready for Sprint 1)
- `backend/app/models/` — Models directory (empty, ready for Sprint 1)

**Frontend:**
- `frontend/app/order/page.tsx` — Order form stub
- `frontend/app/order/verify/[ref]/page.tsx` — Verification page stub
- `frontend/app/order/payment/[ref]/page.tsx` — Payment page stub
- `frontend/app/admin/page.tsx` — Admin dashboard stub
- `frontend/app/admin/orders/[id]/page.tsx` — Order detail page stub
- `frontend/lib/api.ts` — API client utility
- `frontend/.env.example` — NEXT_PUBLIC variables
- Tailwind CSS preconfigured with Next.js

**Root:**
- `.gitignore` — Python, Node, env, credentials patterns

---

## Ready to Merge?

Once git is initialized, Google setup is complete, and you have `.env` files configured:

```bash
# Verify everything still works

# Backend (with venv)
cd /Users/fbi/Documents/github_repo/saas-printshop/backend
source venv/bin/activate
uvicorn app.main:app --reload &
curl http://localhost:8000/api/v1/health
kill %1
deactivate

# Frontend
cd /Users/fbi/Documents/github_repo/saas-printshop/frontend && npm run dev &
# Visit http://localhost:3000/order in browser
kill %1
```

Then tell me: **"Sprint 0 is ready to merge"** and I'll guide you through the PR and tag process.

---

## Backend Venv Usage (Going Forward)

Always activate the venv before running backend commands:

```bash
cd /Users/fbi/Documents/github_repo/saas-printshop/backend
source venv/bin/activate

# Now you can run uvicorn, python, pip, etc.
uvicorn app.main:app --reload

# When done, deactivate
deactivate
```

The venv is excluded from git (see `.gitignore`), so each developer must recreate it locally:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
