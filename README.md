# Content & Subscription Management REST API

REST API for users, content publishing and subscriptions.

**Stack:** Python 3.12, FastAPI, PostgreSQL, Redis, SQLAlchemy 2.0, Docker, GitHub Actions, Pytest, Swagger/OpenAPI

## Features
- JWT authentication (OAuth2 password flow) with bcrypt password hashing
- Role-based access control: `admin`, `creator`, `subscriber`
- Content drafts, publishing, search and pagination
- Premium content gated behind active subscriptions
- Subscription plans, subscribe / cancel, automatic expiry
- Indexed PostgreSQL schema (composite indexes on hot query paths)
- Redis caching for content listings, plans and subscription checks (invalidated on writes)
- Redis-backed fixed-window rate limiting per client (`X-RateLimit-*` headers, HTTP 429)
- Works without Redis (falls back to in-memory rate limiting, caching disabled)
- Interactive docs at `/docs` (Swagger UI) and `/redoc`

## Run with Docker
```bash
docker compose up --build
```
Open http://localhost:8000/docs. An admin is created from `FIRST_ADMIN_EMAIL` / `FIRST_ADMIN_PASSWORD` in `.env`.

## Run locally
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d db redis
uvicorn app.main:app --reload
```

## Tests
```bash
pytest -q
```
Tests use an in-memory SQLite database, so no services are required.

## Endpoints (prefix `/api/v1`)
| Method | Path | Access |
|---|---|---|
| POST | /auth/register | public |
| POST | /auth/login | public |
| GET | /auth/me | authenticated |
| PATCH | /users/me | authenticated |
| GET | /users, /users/{id} | admin |
| PATCH | /users/{id}/role | admin |
| DELETE | /users/{id} | admin (deactivate) |
| GET | /content | public (published, `page`, `size`, `q`, `premium`) |
| GET | /content/mine | creator, admin |
| GET | /content/{id} | public / subscribers for premium |
| POST | /content | creator, admin |
| PATCH / DELETE | /content/{id} | author, admin |
| POST | /content/{id}/publish, /unpublish | author, admin |
| GET | /subscriptions/plans | public |
| POST | /subscriptions/plans | admin |
| POST | /subscriptions | authenticated |
| GET | /subscriptions/me | authenticated |
| POST | /subscriptions/{id}/cancel | owner, admin |
| GET | /subscriptions | admin |
| GET | /health | public |

## Project structure
```
app/
  main.py            app factory, middleware, routers
  config.py          settings from environment
  database.py        engine & session
  cache.py           Redis cache and rate-limit store
  models.py          SQLAlchemy models
  schemas.py         Pydantic schemas
  auth/              JWT + dependencies (RBAC)
  routers/           HTTP endpoints
  services/          business logic
tests/               pytest suite
```
