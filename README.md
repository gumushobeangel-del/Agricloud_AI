# AgriCloud AI

AgriCloud AI is a Uganda-focused agricultural intelligence platform with a Django REST API and a React + TypeScript dashboard. It is designed to combine farmer-managed farm records with NASA POWER climate observations and explainable, rules-based guidance.

## What is included

- JWT registration, login and profile endpoints with farmer, extension and administrator roles.
- Farm create, update, list and delete endpoints, scoped to the authenticated user (extension/admin users can review records).
- NASA POWER daily climate retrieval on the backend, parameter/date validation, caching, missing-value handling and a clearly separated historical-observation response.
- Transparent planting guidance based on the farm's crop, soil and available climate data. It is advisory, not a substitute for local agronomic expertise.
- Dark forest-green responsive dashboard, farm management, weather view and planting advisor.
- OpenStreetMap/Leaflet farm map, Recharts climate visualization, loading/error/empty states.
- API documentation at `/api/docs/`.

The app does not ship fabricated live weather or farm records. A new account starts with an empty dashboard; add a farm with valid coordinates to retrieve NASA POWER data.

## Requirements

- Python 3.11+
- Node.js 20+
- PostgreSQL 14+ for deployment. SQLite is the local default to make first-run setup simple.

## Windows PowerShell setup

From the project root in Windows PowerShell:

```powershell
Set-Location C:\Users\THINKPAD\Desktop\Agricloud_AI
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py createsuperuser
.\.venv\Scripts\python.exe backend\manage.py runserver
```

In a second PowerShell terminal:

```powershell
Set-Location C:\Users\THINKPAD\Desktop\Agricloud_AI\frontend
npm.cmd install
npm.cmd run dev
```

Open the Vite URL (normally `http://localhost:5173`). The frontend proxies `/api` requests to Django at `http://127.0.0.1:8000`.

To use PostgreSQL, set `DB_ENGINE=postgresql`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` in `.env`, then run migrations. `DJANGO_SECRET_KEY` and `ALLOWED_HOSTS` must be set appropriately in production. Never put secrets in frontend variables.

## API outline

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/register/` | Create account and return JWT tokens |
| POST | `/api/auth/token/` | Obtain JWT tokens |
| POST | `/api/auth/token/refresh/` | Refresh access token |
| POST | `/api/auth/logout/` | Revoke the supplied refresh token |
| GET/PATCH | `/api/auth/me/` | View or update current profile |
| GET/POST | `/api/farms/` | List or create farms |
| GET/PATCH/DELETE | `/api/farms/{id}/` | Read or manage an authorized farm |
| GET | `/api/crops/` | List active, source-verified crop catalog entries |
| POST/PATCH/DELETE | `/api/crops/` | Manage crop catalog entries (administrator role only) |
| GET | `/api/weather/?farm_id={id}` | Cached NASA POWER daily observations for a farm |
| POST | `/api/recommendations/` | Generate an explainable planting advisory |
| GET | `/api/risks/?farm_id={id}` | Apply transparent preliminary screens to historical observations |
| POST | `/api/assistant/chat/` | Ask a grounded question when the server LLM and knowledge context are configured |
| GET/POST | `/api/questions/` | List authorized farm questions or submit a question for an owned farm |
| POST | `/api/questions/{id}/respond/` | Reply to a farmer question (extension/admin only) |
| GET | `/api/notifications/` | List the signed-in user's notification records |
| POST | `/api/notifications/{id}/read/` | Mark an owned notification as read |
| GET | `/api/health/` | API health check |

Weather requests accept `start` and `end` dates (`YYYY-MM-DD`) and are restricted to valid POWER periods. NASA observations are historical/observed data and are not forecasts. The NASA POWER service is subject to upstream availability and its own temporal coverage; errors are returned explicitly.

The assistant is enabled when `LLM_API_KEY` and `LLM_MODEL` are set on the server and `LLM_API_BASE_URL` uses HTTPS. `AGRICULTURE_KNOWLEDGE_CONTEXT` is optional but recommended for source-grounded, Uganda-specific answers. To enable it locally, put your provider's actual values in the project-root `.env` (the provider must support the OpenAI-compatible `/chat/completions` endpoint):

```dotenv
LLM_API_KEY=
LLM_API_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini
AGRICULTURE_KNOWLEDGE_CONTEXT="Source: <reviewed guide title> (URL: <official source URL>)\n\n<reviewed passage relevant to farmer questions>"
```

Replace every placeholder with your own provider configuration and reviewed, source-attributed agricultural material; the example is not a knowledge source. Matching paragraphs are sent to the model with their source titles. The assistant also supports conversational follow-ups and can give cautious general responses when no verified paragraph matches; those responses are labeled as not locally verified, and the assistant is instructed not to invent sources, diagnoses, or treatment rates. It uses recent user questions to retrieve context for follow-ups. Restart Django after editing `.env`. Keep the key server-side and never commit `.env`; provider keys and saved farm/account details are never sent from the browser. Without valid provider configuration, the endpoint returns HTTP 503.

Administrators can sign into Django Admin at `/admin/` to manage users, assign extension/admin roles, and maintain the source-verified crop catalog. The initial superuser is created with the command above.

## Security and production notes

- Set `DEBUG=False`, a unique secret key, secure cookie/HTTPS settings, explicit CORS/hosts and PostgreSQL credentials before deployment.
- Configure HTTPS at the reverse proxy. Do not expose database credentials or API tokens in the browser.
- The SPA keeps JWTs in browser storage for this starter implementation. For a public production deployment, consider moving refresh tokens to secure, HttpOnly cookies and add a reviewed CSRF strategy.
- The default development database is SQLite; PostgreSQL is supported via environment variables.
- The built-in recommendation rules are deliberately conservative and show their basis. LLM access requires server-side configuration and vetted Uganda-specific knowledge sources.
- User data is not visible to other farmers. Extension/admin review endpoints require those roles.

## Checks

```powershell
python backend\manage.py test
Set-Location frontend
npm.cmd run build
```

