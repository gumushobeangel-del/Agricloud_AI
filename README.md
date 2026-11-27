# AgriCloud AI

AgriCloud AI is a Uganda-focused agricultural intelligence platform with a Django REST API and a React + TypeScript dashboard. It is designed to combine farmer-managed farm records with NASA POWER climate observations and explainable, rules-based guidance.

## What is included

- JWT registration, login and profile endpoints with farmer, extension and administrator roles, including validated profile-picture uploads.
- Farm create, update, list and delete endpoints, scoped to the authenticated user (extension/admin users can review records).
- Open-Meteo current model conditions and a seven-day forecast for saved farm coordinates, separately labeled from historical observations.
- NASA POWER daily climate retrieval on the backend, parameter/date validation, caching, missing-value handling and a clearly separated historical-observation response.
- Transparent planting guidance based on the farm's crop, soil and available climate data. It is advisory, not a substitute for local agronomic expertise.
- AI-assisted crop image assessment using an optional, server-configured vision model, with model-reported confidence and cautious care suggestions.
- Seven-day irrigation planning using Open-Meteo FAO reference evapotranspiration, forecast rainfall, crop stage and farm area.
- Harvest tracking and a farm-specific yield reference estimate from recorded annual harvests or sourced yield benchmarks, with recent historical climate signals shown separately.
- Uganda commodity-price comparisons and trends from attributed WFP market observations, supplemented by administrator-entered records.
- Dark forest-green responsive dashboard, farm management, weather view, planting advisor, yield forecast and market intelligence.
- OpenStreetMap/Leaflet farm map, Recharts climate visualization, loading/error/empty states.
- API documentation at `/api/docs/`.

The app does not ship fabricated live weather or farm records. A new account starts with an empty dashboard; add a farm with valid coordinates to retrieve current model-based weather and NASA POWER historical data.

Authenticated users can upload a JPEG, PNG, or WebP profile picture up to 5 MB from Profile settings. Local uploads are stored under `backend\media`; configure durable media storage and serving before production deployment.

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
| GET | `/api/admin/overview/` | Administrator-only system totals for accounts, farms, questions and reference data |
| GET | `/api/admin/users/` | Administrator-only account directory |
| PATCH | `/api/admin/users/{id}/` | Change a user's role or active status (the last active administrator is protected) |
| GET/POST | `/api/admin/yield-benchmarks/` | List or add sourced district/national yield benchmarks (administrator only) |
| GET/PATCH/DELETE | `/api/admin/yield-benchmarks/{id}/` | Maintain yield benchmark records (administrator only) |
| GET/POST | `/api/admin/market-prices/` | List or add sourced market observations (administrator only) |
| GET/PATCH/DELETE | `/api/admin/market-prices/{id}/` | Maintain market observation records (administrator only) |
| POST | `/api/auth/me/profile-image/` | Upload or replace the signed-in user's profile picture |
| DELETE | `/api/auth/me/profile-image/` | Remove the signed-in user's profile picture |
| GET/POST | `/api/farms/` | List or create farms |
| GET/PATCH/DELETE | `/api/farms/{id}/` | Read or manage an authorized farm |
| GET | `/api/crops/` | List active, source-verified crop catalog entries |
| POST/PATCH/DELETE | `/api/crops/` | Manage crop catalog entries (administrator role only) |
| GET | `/api/weather/current/?farm_id={id}` | Cached Open-Meteo modelled current conditions and seven-day forecast |
| POST | `/api/crop-disease/` | Analyze a JPEG/PNG/WebP crop image (up to 5 MB) with the configured vision model |
| POST | `/api/irrigation/` | Estimate seven-day crop water demand and irrigation schedule for an authorized farm |
| GET | `/api/yield-forecast/?farm_id={id}&crop={name}` | Estimate harvest from farm history or a sourced district/national benchmark and return climate context |
| GET/POST | `/api/harvests/` | List authorized harvest records or add an actual harvest for an owned farm |
| GET | `/api/market-intelligence/` | List attributed price observations from the last 12 months; optional `commodity` and `district` filters |
| GET | `/api/weather/?farm_id={id}` | Cached NASA POWER daily observations for a farm |
| POST | `/api/recommendations/` | Generate an explainable planting advisory |
| GET | `/api/risks/?farm_id={id}` | Apply transparent preliminary screens to historical observations |
| POST | `/api/assistant/chat/` | Ask a grounded question when the server LLM and knowledge context are configured |
| GET/POST | `/api/questions/` | List authorized farm questions or submit a question for an owned farm |
| POST | `/api/questions/{id}/respond/` | Reply to a farmer question (extension/admin only) |
| GET | `/api/notifications/` | List the signed-in user's notification records |
| POST | `/api/notifications/{id}/read/` | Mark an owned notification as read |
| GET | `/api/health/` | API health check |

The current weather endpoint returns provider model estimates and a seven-day forecast, not local weather-station readings. It is refreshed every 15 minutes and links to Open-Meteo for attribution. Farm coordinates are sent to Open-Meteo by the backend to retrieve the location-specific data. NASA POWER requests accept `start` and `end` dates (`YYYY-MM-DD`) and return historical daily observations, not current conditions or forecasts. Both providers can be unavailable; errors are returned explicitly.

The assistant is enabled when `LLM_API_KEY` and `LLM_MODEL` are set on the server and `LLM_API_BASE_URL` uses HTTPS. `AGRICULTURE_KNOWLEDGE_CONTEXT` is optional but recommended for source-grounded, Uganda-specific answers. To enable it locally, put your provider's actual values in the project-root `.env` (the provider must support the OpenAI-compatible `/chat/completions` endpoint):

```dotenv
LLM_API_KEY=
LLM_API_BASE_URL=https://openrouter.ai/api/v1
LLM_MODEL=openai/gpt-4o-mini
AGRICULTURE_KNOWLEDGE_CONTEXT="Source: <reviewed guide title> (URL: <official source URL>)\n\n<reviewed passage relevant to farmer questions>"
```

Replace every placeholder with your own provider configuration and reviewed, source-attributed agricultural material; the example is not a knowledge source. Matching paragraphs are sent to the model with their source titles. The assistant also supports conversational follow-ups and can give cautious general responses when no verified paragraph matches; those responses are labeled as not locally verified, and the assistant is instructed not to invent sources, diagnoses, or treatment rates. It uses recent user questions to retrieve context for follow-ups. Restart Django after editing `.env`. Keep the key server-side and never commit `.env`; provider keys and saved farm/account details are never sent from the browser. Without valid provider configuration, the endpoint returns HTTP 503.

Crop image analysis is controlled by `CROP_VISION_ENABLED` and `CROP_VISION_PROVIDER`. The configured `roboflow` provider uses `CROP_VISION_API_KEY`, `CROP_VISION_MODEL` (for example, a Roboflow `project/version` identifier), and the HTTPS `CROP_VISION_API_URL`. `openai-compatible` uses the OpenAI-compatible `LLM_API_BASE_URL`, `CROP_VISION_API_KEY` (or `LLM_API_KEY`), and a vision-capable model. The image is sent to the configured provider and is not stored by AgriCloud. The response is an AI-assisted assessment, not a confirmed diagnosis; model-reported confidence is uncalibrated. A classifier only returns its class and score; it does not identify individual symptoms or validate a treatment. Confirm suspected disease with an extension worker before treating crops. Unsupported providers or missing configuration return HTTP 503.

Smart irrigation requests the Open-Meteo seven-day forecast including FAO reference evapotranspiration. It applies indicative crop-stage coefficients and estimates effective rainfall at 80%; soil-texture scheduling triggers are approximate, not sensor-calibrated. A low farmer-entered soil-moisture estimate lowers the schedule trigger for closer field checks, but does not change calculated water volumes; no farm sensor is connected. Forecast provider failures or missing required weather values are returned as errors rather than replaced with synthetic data.

Yield estimates use the farm's average recorded annual production when available, otherwise the latest district-specific or national benchmark multiplied by farm area. Recent NASA POWER climate screens are displayed as context but do not modify the estimate. This is a sourced reference calculation, not a trained machine-learning or climate-adjusted forecast. A Hugging Face token alone does not identify or supply a validated Uganda yield model; no remote model is called. Without harvest history or a benchmark, no quantity is generated. Log actual season totals to build farm production trends.

Market intelligence imports the public [WFP Uganda Food Prices dataset on HDX](https://data.humdata.org/dataset/wfp-food-prices-for-uganda), including each observation's date, market, district, currency, unit, retail/wholesale type, and source attribution. The feed is cached for six hours and older than one year or future-dated observations are excluded. These are survey observations, not guaranteed current farm-gate buying offers. Price spreads compare only matching commodities, units, currencies, and price types, and exclude transport, quality and fees. If the WFP feed is unavailable, the API reports that condition and shows any available administrator-entered records. The dataset is provided under [CC BY-IGO](https://creativecommons.org/licenses/by/3.0/igo/legalcode).

Administrators can use the in-app **System administration** control room to manage user roles/access, maintain the source-verified crop catalog, add sourced yield benchmarks, and enter or remove market-price observations with their market, district, unit, currency, observation date and source URL. Django Admin remains available at `/admin/` for broader database maintenance. No sample yield values or market prices are preloaded. The initial superuser is created with the command above and is automatically assigned the AgriCloud Administrator role when migrations are applied.

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

