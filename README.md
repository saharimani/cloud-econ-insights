# Cloud Economics Insights API

[![tests](https://github.com/saharimani/cloud-econ-insights/actions/workflows/tests.yml/badge.svg)](https://github.com/saharimani/cloud-econ-insights/actions/workflows/tests.yml)

A Flask REST API for saving economic indicators and pulling their values from the **World Bank Open Data API**. Users register, get an API key, and can only see their own data.

This is a three-person group project for **ECS781P Cloud Computing** at Queen Mary University of London (December 2025). It is a coursework prototype, not a production service.

`Python 3.11` · `Flask` · `Flask-SQLAlchemy` · `SQLite / PostgreSQL` · `requests` · `Docker` · `Gunicorn` · `Google Cloud`

## Endpoints

| Method | Path | What it does |
|---|---|---|
| POST | `/auth/register` | Create an account; returns an API key (shown once) |
| POST | `/auth/login` | Issue a new API key; the previous one stops working |
| GET / POST | `/indicators/` | List or create your indicators (e.g. `NY.GDP.MKTP.KD.ZG`, GDP growth) |
| GET / POST | `/snapshots/` | List (filter by `indicator_id`, `country`, `year`) or create a snapshot by hand |
| **POST** | **`/snapshots/fetch`** | **Fetch the live value from the World Bank for one of your indicators, then store it** |
| GET / PUT / DELETE | `/snapshots/<id>` | Read, update or delete one of your snapshots |

Every endpoint except `/auth/*` requires the `X-API-KEY` header.

## Example

```bash
# register and keep the key
curl -s -X POST localhost:8080/auth/register -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"change-this-password"}'

# save an indicator
curl -s -X POST localhost:8080/indicators/ -H "X-API-KEY: $KEY" -H "Content-Type: application/json" \
  -d '{"code":"NY.GDP.MKTP.KD.ZG","name":"GDP growth (annual %)"}'

# pull the UK's 2022 value from the World Bank and store it
curl -s -X POST localhost:8080/snapshots/fetch -H "X-API-KEY: $KEY" -H "Content-Type: application/json" \
  -d '{"indicator_id":1,"country":"GB","year":2022}'
```

## Security

- Passwords are hashed with Werkzeug.
- API keys are 256-bit random tokens. Only their SHA-256 hash is stored, and logging in rotates the key.
- Every query is scoped to the authenticated user. Another user's record returns 404, so the API doesn't reveal which records exist.
- Input is validated before it reaches the database or the World Bank. Country and indicator codes are checked against strict patterns because they become part of the outbound URL.
- Debug mode is off by default, and there is no hard-coded secret key.

## Tests

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

The tests run on every push (GitHub Actions) and cover:
- **Authentication:** input validation, hashed and rotated keys.
- **Isolation between users:** one user can't read, edit, delete or fetch against another user's records.
- **World Bank integration:** the client parses the real response shape and handles empty data, errors and timeouts. The fetch endpoint stores the value it gets back, returns 502 when there is no value, and rejects unsafe codes before making any request. The HTTP call is stubbed, so the tests never reach the internet.

## Running it

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python app.py                     # http://127.0.0.1:8080
```

The app uses a local SQLite file by default. Set `DATABASE_URL` to use PostgreSQL. The `Dockerfile` serves the app with Gunicorn on `$PORT`, which is how it runs on Cloud Run.

## Team

Contributions as recorded in the commit history:

- **Sahar Imani** ([saharimani](https://github.com/saharimani)): original application structure (Flask app factory, configuration, SQLAlchemy models, authentication helpers, route blueprints) and the World Bank API client. Later work: the security hardening, the `/snapshots/fetch` endpoint and the test suite.
- **Sara Alrassi** ([Sara-Alr](https://github.com/Sara-Alr)): authentication, indicator and snapshot endpoint development.
- **Uhunoma Osemwengie** ([uhunomaosem](https://github.com/uhunomaosem)): Docker containerisation and deployment on Google Cloud.

## Limitations

- **No database migrations.** Tables are created on start-up.
- **No rate limiting, and the World Bank call is synchronous.** A slow upstream response holds a worker for up to 25 s.
- **Only Cloud Run's own HTTPS.** There is no separate secret manager or TLS setup.
- **No integration tests against a deployed instance.**

## Layout

```
app.py              application factory
config.py           configuration from environment variables
models.py           User, Indicator, EconSnapshot
auth.py             password hashing, API-key issue/rotation, require_api_key decorator
external_api.py     World Bank API client
routes/             auth, indicators and snapshots blueprints
tests/              security and World Bank tests
Dockerfile          Gunicorn container for Cloud Run
```
