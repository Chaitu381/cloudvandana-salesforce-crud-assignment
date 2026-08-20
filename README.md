## 👨‍💻 Author

**Chaitanya Pilla**

- GitHub: [github.com/Chaitu381](https://github.com/Chaitu381)
- Repository: [cloudvandana-salesforce-crud-assignment](https://github.com/Chaitu381/cloudvandana-salesforce-crud-assignment)
- Live Demo: [cloudvandana-salesforce-crud-chaitanya.onrender.com](https://cloudvandana-salesforce-crud-chaitanya.onrender.com)
- LinkedIn: [https://www.linkedin.com/in/chaitu381/](https://www.linkedin.com/in/chaitu381/)
- Portfolio: [https://portfolio.fengari.me/](https://portfolio.fengari.me/)
- Email: [chaitu38192021@gmail.com](chaitu38192021@gmail.com)
- Phone Number: +91 6309909924

---

# CloudVandana Salesforce CRUD Assignment

A full-stack Salesforce CRUD application developed for the **CloudVandana Associate Software Engineer Assignment**.

The application authenticates users with Salesforce OAuth 2.0 and allows users to manage Salesforce standard objects directly from a custom web interface.

## 🌐 Live Demo

### [Open Application](https://cloudvandana-salesforce-crud-chaitanya.onrender.com)

> **Note:** The application is hosted on Render's free tier. If the service has been inactive, the first request may take approximately **30–60 seconds** to start.

---

## ✨ Features

- Salesforce OAuth 2.0 authentication
- Authorization Code Flow with PKCE
- CRUD operations for:
  - Account
  - Opportunity
  - Lead
  - Contact
  - Case
- Dynamic Salesforce field metadata
- Select between 5–10 fields
- Create, View, Update and Delete records
- Loads 20 records at a time
- Infinite scrolling
- Secure HttpOnly sessions
- Automatic Salesforce token refresh
- Responsive React interface
- Dockerized full-stack deployment

---

## 🛠 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, TypeScript, Vite |
| Backend | FastAPI, Python |
| API | Salesforce REST API |
| Authentication | Salesforce OAuth 2.0 + PKCE |
| HTTP Client | HTTPX |
| Deployment | Docker, Render |
| Source Control | GitHub |

---

## 🏗 Architecture

```text
User
 │
 ▼
React + TypeScript
 │
 ▼
FastAPI Backend
 │
 ▼
Salesforce OAuth 2.0
 │
 ▼
Salesforce REST API
 │
 ├── Account
 ├── Opportunity
 ├── Lead
 ├── Contact
 └── Case
```

---

## 🚀 Run Locally

### 1. Clone the repository

```bash
git clone https://github.com/Chaitu381/cloudvandana-salesforce-crud-assignment.git

cd cloudvandana-salesforce-crud-assignment
```

### 2. Create the environment file

Windows:

```cmd
copy .env.example .env
```

Linux / macOS:

```bash
cp .env.example .env
```

Configure the following values:

```env
ENVIRONMENT=development

APP_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:8000
ALLOWED_ORIGINS=http://localhost:8000

COOKIE_SECURE=false

SESSION_SECRET=YOUR_RANDOM_SECRET

SF_AUTH_BASE_URL=https://login.salesforce.com
SF_CLIENT_ID=YOUR_SALESFORCE_CONSUMER_KEY
SF_CLIENT_SECRET=YOUR_SALESFORCE_CONSUMER_SECRET

SF_API_VERSION=v67.0
SF_SCOPES=api refresh_token
```

> Never commit your `.env`, Salesforce Consumer Secret, access token, refresh token, or session secret to GitHub.

### 3. Configure Salesforce OAuth

Create a Salesforce **External Client App** and configure the local callback URL:

```text
http://localhost:8000/api/auth/callback
```

Required OAuth scopes:

```text
Manage user data via APIs (api)

Perform requests at any time
(refresh_token, offline_access)
```

### 4. Start the application

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000
```

---

## ☁️ Production Deployment

The application is deployed as a single Docker service on **Render**.

### Live URL

https://cloudvandana-salesforce-crud-chaitanya.onrender.com

### Salesforce Production Callback

```text
https://cloudvandana-salesforce-crud-chaitanya.onrender.com/api/auth/callback
```

Production secrets are configured using **Render Environment Variables** and are not stored in the GitHub repository.

---

## 🧪 Testing

Backend tests:

```bash
cd backend
pytest -q
```

Frontend production build:

```bash
cd frontend
npm install
npm run build
```

---

## 🔐 Security

- Salesforce Consumer Secret remains backend-only
- OAuth access and refresh tokens are not stored in `localStorage`
- Encrypted HttpOnly cookies are used for sessions
- PKCE is used during OAuth authentication
- Salesforce objects and fields are validated server-side
- Record IDs are validated before API operations
- `.env` and application secrets are excluded from Git

---

## 📌 Assignment

**CloudVandana — Associate Software Engineer Assignment**

The project demonstrates a secure full-stack integration with Salesforce using OAuth 2.0 and the Salesforce REST API.
