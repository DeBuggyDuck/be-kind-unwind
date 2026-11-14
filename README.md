# Be Kind, Unwind

Mood- and bandwidth-driven media curation backend built with Flask.

## 1. Setup

1. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install pinned dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure your local `.env` file (see **Environment Variables** below).

4. Run the development server:
   ```bash
   flask --app "be_kind_unwind:create_app('development')" run --port 5001
   ```

## 2. Environment Variables

Copy `.env.example` to `.env` before starting the app, then replace the placeholder values with local settings:

```bash
cp .env.example .env
```

- `DATABASE_URL` — Connection URI for the application database (for example, `sqlite:///instance/dev.db` for local SQLite or `postgresql://USER:PASSWORD@HOST:PORT/DBNAME` for Postgres). Tells SQLAlchemy where to store and query application data.
- `JWT_SECRET` — Secret signing key used to sign and verify JSON Web Tokens (JWTs) for user authentication. Must be a strong, private value (required at startup in production).

## 3. Database & Migrations Status

- **Current database:** Local SQLite development database (`instance/dev.db` via `DATABASE_URL`).
- **Migrations status:** Migrations not yet configured (`Flask-Migrate` is wired in `extensions.py`, but `flask db init` and initial migration versions have not been generated yet).
