# portfolio_analytics_platform

Front-end + API layer for the investment analytics platform: three dashboards —
**Price Viewer** (prices by source), **Positioning** (holdings + weights), and
**Contribution** (per-holding contribution to portfolio return).

> **Reference data only.** This repo's backend is *disposable scaffolding* built to
> develop the front end. The authoritative ETL backend (PostgreSQL + psycopg v3)
> lives on a different machine. Here, a SQLite "reference DB" stands in, seeded with
> representative sample data following the documented schema. Porting to the real
> backend is mechanical — swap `src/db/session.py` internals for psycopg and change
> `?` placeholders to `%s`. The HTTP/JSON API and the Next.js bundle port unchanged.

## Layout

```
src/db/            reference backend: SQLite session, schema/*.sql, seed, build script
web/api/           FastAPI app (routes/ + services/) — JSON API on /api/...
web/apps/dashboards/  Next.js 14 static-export app (the three dashboards)
data/reference.db  generated SQLite DB (gitignored — rebuild any time)
```

## Run it (development)

Three one-time / per-session steps. Use a `bash` shell.

**1. Python deps** (corporate SSL interception requires the trusted-host flags):
```bash
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org \
    fastapi "uvicorn[standard]"
```

**2. Build the reference DB** (creates `data/reference.db`):
```bash
PYTHONPATH=. python src/db/build_reference_db.py
```

**3a. Start the API** (terminal A):
```bash
PYTHONPATH=. python -m uvicorn web.api.main:app --reload --port 8000
```

**3b. Start the front end** (terminal B):
```bash
cd web/apps/dashboards
npm config set strict-ssl false      # one-time: corporate SSL interception
npm install
npm run dev                          # http://localhost:3000
```
The dev server reads `NEXT_PUBLIC_API_BASE=http://localhost:8000` from
`.env.development` and the API allows CORS from `:3000`.

## Production-style serve (single origin, no Node runtime)

```bash
cd web/apps/dashboards && npm run build   # emits out/ (static bundle)
# then, from repo root:
PYTHONPATH=. python -m uvicorn web.api.main:app --port 8000
```
FastAPI serves the built bundle at `/` and the API at `/api` on the **same origin**
(relative URLs, no CORS). Open http://localhost:8000.

## API endpoints

| Endpoint | Dashboard |
|---|---|
| `GET /api/securities?search=&limit=` | Price Viewer (picker) |
| `GET /api/prices?entity_id=&from=&to=&sources=` | Price Viewer |
| `GET /api/portfolios` | all (picker) |
| `GET /api/portfolios/{id}/dates` | Positioning / Contribution |
| `GET /api/portfolios/{id}/holdings?date=` | Positioning |
| `GET /api/portfolios/{id}/contribution?from=&to=&source=` | Contribution |
| `GET /api/health` | health check |
