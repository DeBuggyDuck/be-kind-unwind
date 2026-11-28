# Be Kind, Unwind

A RESTful Flask backend API for tracking daily mood check-ins and personalized wellness recommendations, backed by SQLAlchemy, Alembic migrations, JWT authentication, and PostgreSQL.

## Tech Stack
- **Framework:** Python 3.12, Flask (Application Factory pattern)
- **Database & Migrations:** SQLAlchemy, Flask-Migrate (Alembic), SQLite (local dev) / PostgreSQL 16 (Docker)
- **Authentication:** Stateless JWT (`PyJWT`)
- **Production Server:** Gunicorn
- **Containerization:** Docker & Docker Compose

---

## Local Setup (Without Docker)

### 1. Clone and create a virtual environment
```bash
git clone <your-repo-url>
cd be-kind-unwind
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables
Copy `.env.example` to `.env` and adjust values for local development (for local SQLite, `DATABASE_URL` can be omitted or set to `sqlite:///dev.db`):

```bash
cp .env.example .env
```

### 3. Initialize the database and run
```bash
flask --app wsgi db upgrade
flask --app wsgi run --port 8000
```

---

## Run with Docker Compose + Postgres

### 1. Prerequisites
- **Docker** and **Docker Compose** (v2+) installed and running.

### 2. Environment setup
Copy the example environment file to `.env`:

```bash
cp .env.example .env
```

Open `.env` and set consistent values for PostgreSQL and the Flask API:

```env
FLASK_ENV=development
POSTGRES_USER=unwind_user
POSTGRES_PASSWORD=unwind_pass
POSTGRES_DB=be_kind_unwind
DATABASE_URL=postgresql+psycopg://unwind_user:unwind_pass@db:5432/be_kind_unwind
JWT_SECRET_KEY=replace-with-a-random-secret
```

- Make sure the username, password, and database name in `DATABASE_URL` match `POSTGRES_USER`, `POSTGRES_PASSWORD`, and `POSTGRES_DB`, and keep `@db:5432` as the host (the Compose service name).
- `.env` is ignored by Git (`.gitignore`) and must never be committed—all real secrets live only in `.env`.

### 3. Start the stack
Build the web image and start both `db` (PostgreSQL 16) and `web` (Gunicorn/Flask):

```bash
docker compose up --build
```

For subsequent runs (or to run in the background), use:

```bash
docker compose up -d
```

The API will listen on `http://localhost:8000` once `db` passes its healthcheck.

### 4. Run migrations inside the container
Apply the Alembic database migrations against PostgreSQL from inside the running `web` container:

```bash
docker compose exec web flask --app wsgi db upgrade
```

### 5. Smoke test the API
Verify registration, JWT login, and session creation end-to-end:

```bash
# 1. Register a user (returns 201 on first run, or 409 if compose_user already exists)
curl -s -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"compose_user","email":"compose@example.com","password":"secret"}'

# 2. Log in and capture the JWT
TOKEN=$(curl -s -X POST http://localhost:8000/login \
  -H "Content-Type: application/json" \
  -d '{"username":"compose_user","password":"secret"}' | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")

# 3. Create a mood check session
curl -s -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"mood":"anxious","attention_span":"short","time_commitment":10,"recommendation":"Take a 10-minute guided breathwork break","notes":"Testing Postgres persistence"}'
```

### 6. Persistence check
Verify that records survive container restarts via the named `postgres_data` volume:

```bash
# Stop and recreate containers (do NOT pass -v, which deletes volumes)
docker compose down
docker compose up -d

# Fetch sessions using your JWT and confirm the created record is still returned
curl -s -X GET http://localhost:8000/api/sessions \
  -H "Authorization: Bearer $TOKEN"
```