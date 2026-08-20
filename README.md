# Salesforce Object Manager — CloudVandana ASE Assignment

Production-ready React + TypeScript + FastAPI application for CRUD operations on Salesforce **Account, Opportunity, Lead, Contact, and Case** records.

## What is implemented

- Salesforce External Client App OAuth 2.0 **Authorization Code + PKCE (S256)**.
- Optional/expected confidential-client secret kept only on the FastAPI backend.
- OAuth access/refresh tokens stored in an **encrypted HttpOnly cookie**, never in browser storage.
- Automatic refresh-token retry when Salesforce returns an expired-session response.
- Central dropdown for Account, Opportunity, Lead, Contact, Case.
- Salesforce `describe` metadata drives field labels, types, permissions, required fields, and picklists.
- User-selectable **5–10 display fields** with per-object browser preference.
- Create, view, edit, delete workflows.
- Infinite scrolling in **exact pages of 20** using signed/encrypted keyset cursors.
- Field/object whitelisting, record-ID validation, origin checks for mutations, production HTTPS checks.
- Single-container production build: FastAPI serves the compiled React application.
- Backend unit tests plus frontend TypeScript production-build checks in CI.
- Docker, Docker Compose, and Render blueprint.

## Salesforce setup

1. Create a Salesforce Developer Org.
2. In **Setup → External Client App Manager**, create a new External Client App.
3. Enable OAuth.
4. Callback URL for local development:
   `http://localhost:8000/api/auth/callback`
5. Add OAuth scopes:
   - **Manage user data via APIs (`api`)**
   - **Perform requests at any time (`refresh_token`, `offline_access`)**
6. Enable/require **PKCE** for supported authorization flows.
7. For this backend-based confidential client, configure **Require Secret for Web Server Flow** and **Require Secret for Refresh Token Flow** if your ECA policy uses a secret.
8. Copy the Consumer Key and Consumer Secret into `.env`.
9. Ensure the Salesforce user/profile or permission set has API access and CRUD/FLS permissions for the five standard objects.

For a sandbox, set `SF_AUTH_BASE_URL=https://test.salesforce.com`.

## Local development

### Backend

```bash
cp .env.example .env
# Fill SF_CLIENT_ID, SF_CLIENT_SECRET, and SESSION_SECRET
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements-dev.txt
cd backend
uvicorn app.main:app --reload --port 8000
```

### Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Production / Docker

For a single production URL, set:

```env
ENVIRONMENT=production
APP_BASE_URL=https://YOUR-HOST
FRONTEND_URL=https://YOUR-HOST
ALLOWED_ORIGINS=https://YOUR-HOST
COOKIE_SECURE=true
SESSION_SECRET=<unique random secret 32+ chars>
SF_CLIENT_ID=<consumer key>
SF_CLIENT_SECRET=<consumer secret>
SF_API_VERSION=v67.0
```

Update the External Client App callback URL to:

`https://YOUR-HOST/api/auth/callback`

Then:

```bash
docker build -t salesforce-object-manager .
docker run --env-file .env -p 8000:8000 salesforce-object-manager
```

## Render free deployment

1. Push this repository to GitHub.
2. In Render, create a Blueprint from the repository (`render.yaml`).
3. Set `SF_CLIENT_ID` and `SF_CLIENT_SECRET`.
4. Set `APP_BASE_URL`, `FRONTEND_URL`, and `ALLOWED_ORIGINS` to the exact Render HTTPS service URL.
5. Add the exact `/api/auth/callback` HTTPS URL to the Salesforce External Client App.
6. Deploy and test login plus CRUD for all five objects.

## Verification commands

```bash
cd backend
pytest -q

cd ../frontend
npm install
npm run build
```

## Notes

- The app intentionally uses Salesforce REST API **v67.0 (Summer '26)** by default; override with `SF_API_VERSION` if required by the target org.
- No Salesforce data is stored in a local application database.
- The five-object allowlist is enforced server-side; object names and fields are never accepted blindly into SOQL.
- Pagination uses `(CreatedDate, Id)` keyset ordering instead of `OFFSET`, so it can keep returning exactly 20 records per request without Salesforce OFFSET limitations.
