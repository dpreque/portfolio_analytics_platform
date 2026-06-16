# portfolio_analytics_platform

Front-end + API layer for the investment analytics platform: three dashboards —
**Price Viewer** (prices by source), **Positioning** (holdings + weights), and
**Contribution** (per-holding contribution to portfolio return).

> **Reference data only.** This repo's backend is *disposable scaffolding* built to
> develop the front end. The authoritative ETL backend (PostgreSQL + psycopg v3)
> lives on a different machine. Here, a SQLite "reference DB" stands in, seeded with
> representative sample data following the documented schema. Porting to the real
> backend is mechanical — swap `src/db/connection.py` internals for psycopg and change
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
cd web/apps/dashboards
NODE_TLS_REJECT_UNAUTHORIZED=0 env -u NEXT_PUBLIC_API_BASE npm run build   # emits out/
# then, from repo root:
PYTHONPATH=. python -m uvicorn web.api.main:app --port 8000
```
FastAPI serves the built bundle at `/` and the API at `/api` on the **same origin**
(relative URLs, no CORS). Open http://localhost:8000.

## Release & deploy (dev → GitHub → i7)

Build on the dev machine, ship the bundle as a **GitHub Release zip**, swap it into
`out/` on the i7 (which has no Node). `out/` and `*.zip` are gitignored — source goes
through git, the built bundle goes through a Release.

**On the dev machine**
```bash
cd web/apps/dashboards

# 1. bump the version in package.json (e.g. "version": "1.1.0")

# 2. build the static export (flags below are required in this environment)
NODE_TLS_REJECT_UNAUTHORIZED=0 env -u NEXT_PUBLIC_API_BASE npm run build

# 3. package out/ into a versioned zip (contents sit at the zip root)
VER=$(node -p "require('./package.json').version")
python -c "import shutil; shutil.make_archive('dashboards-'+'$VER', 'zip', root_dir='out')"

# 4. commit + push SOURCE only (out/ and the zip are gitignored)
git add -A && git commit -m "dashboards v$VER" && git push
```
Then on github.com: **Releases → Draft a new release → tag `dash-v<version>` →
upload `dashboards-<version>.zip` as an asset → Publish.**

Why the build flags:
- `NODE_TLS_REJECT_UNAUTHORIZED=0` — lets `next/font` fetch Google Fonts past the
  corporate SSL proxy at build time; the fonts are then **self-hosted** into the
  bundle, so the i7 runtime needs no font CDN (offline-safe).
- `env -u NEXT_PUBLIC_API_BASE` — forces **relative** `/api` URLs (same origin, no
  CORS). Never set this var for a production build.

**On the i7 server** (no Node needed)
```bash
# 1. download dashboards-<version>.zip from the Release page (browser is fine)
# 2. swap it into out/ atomically
cd /path/to/repo/web/apps/dashboards
rm -rf out_new && mkdir out_new && unzip -o ~/Downloads/dashboards-<version>.zip -d out_new
rm -rf out_old; mv out out_old 2>/dev/null; mv out_new out
# 3. (re)start the API so it serves the new bundle (host 0.0.0.0 for the floor subnet)
cd /path/to/repo
PYTHONPATH=. python -m uvicorn web.api.main:app --host 0.0.0.0 --port 8000
```
- **Frontend-only change** → just download + swap the zip (restart only if `out/` was
  absent when uvicorn started).
- **Backend change** → `git pull` the source too, then restart uvicorn.
- **Rollback** → download the previous Release zip and swap it back in.

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
