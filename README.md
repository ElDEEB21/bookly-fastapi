# Bookly

> A REST API for managing books, reviews, and tags — built with FastAPI, PostgreSQL, Redis, and Celery.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-asyncpg-336791?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-blocklist_%26_rate_limit-DC382D?style=flat-square&logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-email_tasks-37814A?style=flat-square)](https://docs.celeryq.dev/)
[![Alembic](https://img.shields.io/badge/Alembic-migrations-lightgrey?style=flat-square)](https://alembic.sqlalchemy.org/)

[Overview](#overview) • [Features](#features) • [Getting started](#getting-started) • [Run the API](#run-the-api) • [API reference](#api-reference) • [Configuration](#configuration) • [Troubleshooting](#troubleshooting) • [Resources](#resources)

## Overview

Bookly is a versioned JSON API (`/api/v1`) for a simple book catalog with user accounts. Users sign up, verify their email, log in with JWT access/refresh tokens, and manage their own books. Books can be reviewed once per user and organized with tags.

The project follows a modular layout with one package per domain (`auth`, `books`, `reviews`, `tags`), a shared `db` layer (SQLModel + async SQLAlchemy), and cross-cutting concerns (error handlers, middleware, mail, background tasks) in `src/`.

```
bookly/
├── src/
│   ├── __init__.py        # FastAPI app factory, router registration (/api/v1)
│   ├── config.py          # Pydantic Settings (.env)
│   ├── errors.py          # Domain exceptions + centralized handlers
│   ├── middleware.py      # Request logging, CORS, TrustedHost
│   ├── mail.py            # FastAPI-Mail configuration
│   ├── celeryTasks.py     # Celery app + send_email task
│   ├── db/
│   │   ├── main.py        # Async engine + session dependency
│   │   ├── models.py      # User, Book, Review, Tag, BookTag
│   │   └── redis.py       # Token blocklist + rate limiting
│   ├── auth/              # Signup, login, verify, refresh, logout, password reset, roles
│   ├── books/             # Book CRUD (owner-scoped)
│   ├── reviews/           # Add a review to a book
│   └── tags/              # Tag CRUD (admin) + attach tags to books
├── migrations/            # Alembic migrations (PostgreSQL)
├── alembic.ini
└── requirements.txt
```

## Features

- **JWT auth with rotation-safe logout**: short-lived access tokens, 2-day refresh tokens, Redis blocklist for revoked JTIs.
- **Email verification + password reset**: signed URL-safe tokens, resend endpoint, Celery-backed delivery via FastAPI-Mail.
- **Role-based access**: `admin` / `user` roles, verification gate on protected routes, owner checks on books (admins bypass).
- **Book catalog**: create, list, list-mine, detail (with reviews), patch, delete.
- **Reviews**: one review per user per book (`rating` 1–5), enforced at the service layer.
- **Tags**: admin-managed tag catalog, many-to-many attach to books via `BookTag`.
- **Hardening**: Redis rate limits on login / resend / password-reset, strong password policy, CORS + TrustedHost middleware, centralized error codes.
- **Async throughout**: SQLModel + `asyncpg`, Alembic migrations, Redis asyncio client.

## Getting started

### Prerequisites

- Python 3.11+ (developed on 3.14.2)
- PostgreSQL 14+
- Redis 6+
- An SMTP account for outgoing mail (e.g. Gmail app password, Mailtrap, Mailhog)

### Set up your local environment

1. Clone the repo and create a virtual environment:

```bash
git clone https://github.com/ElDEEB21/bookly-fastapi.git
cd bookly-fastapi
python -m venv .venv
```

Activate it:

```powershell
# Windows (PowerShell)
.venv\Scripts\activate
```

```bash
# macOS / Linux
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. Create a `.env` file in the project root (see [Configuration](#configuration)):

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/bookly
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=change-me-to-a-long-random-string
JWT_ALGORITHM=HS256
DOMAIN=localhost:8000
SCHEME=http
MAIL_USERNAME=you@example.com
MAIL_PASSWORD=app-password
MAIL_FROM=noreply@example.com
MAIL_FROM_NAME=Bookly
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
```

4. Apply migrations:

```bash
alembic upgrade head
```

> [!TIP]
> `src/db/main.py` converts `postgresql://` to `postgresql+asyncpg://` automatically, so you can keep the plain URL in `.env`. Alembic uses the sync driver via `migrations/env.py`.

## Run the API

Start Redis and PostgreSQL first, then:

```bash
# API with auto-reload
uvicorn src.__init__:app --reload --port 8000
```

```bash
# Celery worker for email delivery (required for signup/verify/reset emails)
celery -A src.celeryTasks.c_app worker --loglevel=info
```

Open the interactive docs:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

> [!IMPORTANT]
> Emails are sent via Celery. If the worker is not running, `signup`, `resend-verification`, and `password-reset-request` will enqueue tasks that never execute. The API itself stays up, but no mail goes out.

> [!NOTE]
> All protected routes require `Authorization: Bearer <access_token>` and a verified account. Unverified users get `403 account_not_verified`.

### Quickstart

```bash
# 1. Sign up
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"first_name":"Ada","last_name":"Lovelace","username":"ada","email":"ada@example.com","password":"Str0ngPass!"}'

# 2. Verify via the link emailed to you:
#    GET /api/v1/auth/verify/{token}

# 3. Log in
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"ada@example.com","password":"Str0ngPass!"}'

# 4. Create a book (use the access_token from login)
curl -X POST http://localhost:8000/api/v1/books \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"The Pragmatic Programmer","author":"Hunt & Thomas","publisher":"Addison-Wesley","published_date":"1999-10-20","page_count":352,"language":"en"}'
```

## API reference

Base URL prefix: `/api/v1`. Authenticated routes need an access token (not a refresh token); token type misuse returns `401`/`403` with `access_token_required` / `refresh_token_required`.

### Auth (`/api/v1/auth`)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| POST | `/signup` | No | Create account, queues verification email. Returns `201`. |
| GET | `/verify/{token}` | No | Verify email with signed token (1h expiry). |
| POST | `/resend-verification` | No | Resend verification email. Rate-limited (3/hour). |
| POST | `/login` | No | Returns `access_token` + `refresh_token`. Rate-limited (5/5 min). |
| POST | `/refresh_token` | Refresh token | Exchange refresh token for a new access token. |
| POST | `/logout` | Access token | Revokes the token JTl via Redis blocklist. |
| GET | `/me` | Access token, verified | Current user with books and reviews. |
| PATCH | `/{user_uid}/role` | Access token, `admin` | Set role to `admin` or `user`. |
| POST | `/password-reset-request` | No | Always returns `200`; emails reset link if account exists. Rate-limited (3/hour). |
| POST | `/password-reset-confirm/{token}` | No | Set a new password with a signed token (1h expiry). |
| POST | `/send_mail` | Access token, `admin` | Send a bulk welcome email via Celery. Body: `{"addresses": ["a@x.com"]}`. |

Password policy: 8–128 chars, must contain an uppercase letter, a lowercase letter, and a digit.

### Books (`/api/v1/books`)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| GET | `/` | Verified | List all books. |
| GET | `/user` | Verified | List books owned by the current user. |
| POST | `/` | Verified | Create a book; stamped with the caller's `user_uid`. Returns `201`. |
| GET | `/{book_uid}` | Verified | Book detail including reviews. `404 book_not_found`. |
| PATCH | `/{book_uid}` | Verified, owner or `admin` | Partial update. `403 not_book_owner` otherwise. |
| DELETE | `/{book_uid}` | Verified, owner or `admin` | Delete. Returns `204`. |

Book payload:

```json
{
  "title": "Dune",
  "author": "Frank Herbert",
  "publisher": "Chilton Books",
  "published_date": "1965-08-01",
  "page_count": 412,
  "language": "en"
}
```

### Reviews (`/api/v1/reviews`)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| POST | `/book/{book_uid}` | Verified | Add one review per user per book. Returns `201`; duplicate returns `409 review_exists`. |

```json
{ "rating": 5, "review_text": "A masterpiece of world-building." }
```

### Tags (`/api/v1/tags`)

| Method | Path | Auth | Description |
| ------ | ---- | ---- | ----------- |
| GET | `/` | Verified | List all tags. |
| POST | `/` | `admin` | Create a tag `{"name": "sci-fi"}`. Duplicate returns `403 tag_exists`. |
| POST | `/book/{book_uid}/tags` | Verified, owner or `admin` | Attach tags `{"tags": [{"name": "sci-fi"}]}`. |
| PUT | `/{tag_uid}` | `admin` | Rename a tag. |
| DELETE | `/{tag_uid}` | `admin` | Delete a tag. Returns `204`. |

### Error codes

Errors are JSON with a stable `error_code`: `user_exists`, `user_not_found`, `book_not_found`, `tag_not_found`, `tag_exists`, `invalid_email_or_password`, `invalid_token`, `token_revoked`, `access_token_required`, `refresh_token_required`, `insufficient_permissions`, `not_book_owner`, `review_exists`, `account_not_verified`, `server_error`.

## Configuration

Settings are loaded by `src/config.py` (Pydantic Settings) from environment / `.env`:

| Variable | Required | Default | Description |
| -------- | -------- | ------- | ----------- |
| `DATABASE_URL` | Yes | — | PostgreSQL URL, e.g. `postgresql://user:pass@localhost:5432/bookly`. |
| `JWT_SECRET` | Yes | — | HMAC secret for JWT + signed email tokens. |
| `JWT_ALGORITHM` | Yes | — | e.g. `HS256`. |
| `REDIS_URL` | Yes | — | Used as Celery broker/backend and for blocklist + rate limits. |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | Yes | — | SMTP credentials. |
| `MAIL_FROM` / `MAIL_FROM_NAME` | Yes | — | Sender identity. |
| `MAIL_SERVER` / `MAIL_PORT` | Yes | — | SMTP host/port. |
| `DOMAIN` | Yes | — | Host used to build verification/reset links (e.g. `localhost:8000`). |
| `SCHEME` | No | `http` | URL scheme for emailed links. |
| `MAIL_STARTTLS` | No | `true` | STARTTLS flag. |
| `MAIL_SSL_TLS` | No | `false` | SSL/TLS flag. |
| `USE_CREDENTIALS` / `VALIDATE_CERTS` | No | `true` | SMTP auth/cert validation. |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:8000` | Comma-separated allowed origins. |
| `TRUSTED_HOSTS` | No | `localhost,127.0.0.1` | Comma-separated trusted hosts. |
| `FIRST_ADMIN_EMAIL` | No | `""` | Reserved for initial admin bootstrap. |

> [!WARNING]
> Never commit `.env`. It is already git-ignored. Use a long random `JWT_SECRET` in production and serve behind HTTPS with correct `SCHEME`, `DOMAIN`, `CORS_ORIGINS`, and `TRUSTED_HOSTS`.

### Useful commands

```bash
# Create a migration after changing src/db/models.py
alembic revision --autogenerate -m "describe change"

# Apply / inspect migrations
alembic upgrade head
alembic history
alembic downgrade -1

# Run tests
pytest
```

## Troubleshooting

**`sqlalchemy.exc.OperationalError` / connection refused to Postgres**
Check `DATABASE_URL`, confirm Postgres is running and reachable, then retry `alembic upgrade head`.

**`redis.exceptions.ConnectionError`**
Check `REDIS_URL` and that `redis-server` is running. Login, resend-verification, password-reset, refresh, and logout all depend on Redis.

**Signup succeeds but no email arrives**
The Celery worker must be running (`celery -A src.celeryTasks.c_app worker --loglevel=info`) with the same `REDIS_URL` and valid SMTP settings. Check the worker logs and spam folder.

**`401 invalid_token` or `token_revoked`**
Access tokens expire after 1 hour. Use `POST /api/v1/auth/refresh_token` with the refresh token, or log in again. Logged-out tokens are intentionally rejected until they expire.

**`403 account_not_verified`**
Call `GET /api/v1/auth/verify/{token}` from the signup email, or `POST /api/v1/auth/resend-verification`.

**`429 Too Many Requests` on login/reset/resend**
Redis rate limits tripped (login 5/5 min, resend/reset 3/hour per email). Wait for the window or use a different test email.

**`403 trusted host` / CORS errors in the browser**
Add your frontend origin to `CORS_ORIGINS` and your host to `TRUSTED_HOSTS`, then restart the API.

## Resources

- [FastAPI documentation](https://fastapi.tiangolo.com/)
- [SQLModel documentation](https://sqlmodel.tiangolo.com/)
- [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Celery + Redis as broker](https://docs.celeryq.dev/en/stable/getting-started/backends-and-brokers/redis.html)
- [FastAPI-Mail](https://github.com/sabuhish/fastapi-mail)
- [PyJWT](https://pyjwt.readthedocs.io/) and [itsdangerous](https://itsdangerous.palletsprojects.com/)
