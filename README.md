![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)

# Containerized App Exercise

Build a containerized app that uses machine learning. See [instructions](./instructions.md) for details.

# FocusCam

Tracks how focused a student is during a study session. A machine learning client analyzes webcam data, MongoDB stores the results, and a Flask web app shows them.

Currently dummy services wired together through MongoDB.

| Subsystem | Directory |
|---|---|
| ML client (Flask, :8000) | `machine-learning-client/` |
| Web app (Flask, :5001) | `web-app/` |
| MongoDB | official `mongo` image |

## Setup

Requires Docker with Compose (Python 3.12+ only for running outside Docker).

```bash
cp env.example .env
```

| Variable | Purpose |
|---|---|
| `MONGO_INITDB_ROOT_USERNAME`, `MONGO_INITDB_ROOT_PASSWORD`, `MONGO_DB` | Mongo credentials and database |
| `WEB_APP_PORT`, `ML_CLIENT_PORT` | Host ports |
| `MONGO_URI` | Only for running outside Docker; compose builds its own |

## Run

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f
```

- Web app: <http://localhost:5001>
- ML client: <http://localhost:8000/health>
- MongoDB: internal only

Inspect the data:

```bash
docker compose exec mongodb mongosh -u admin -p secret \
  --authenticationDatabase admin focuscam --quiet \
  --eval 'db.getCollection("hello").find().toArray()'
```

## Stop

```bash
docker compose down        # keeps data
docker compose down -v     # deletes data
```

Data lives in the `mongo-data` volume.

## Run one service outside Docker

Compose doesn't publish Mongo, so start a standalone one:

```bash
docker run -d --name focuscam-mongo -p 27017:27017 \
  -v focuscam-mongo-data:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secret mongo
```

Then, from `machine-learning-client/` or `web-app/`:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

Both read `MONGO_URI` from the root `.env`. The web app runs on :5000 locally and finds the ML client at `http://localhost:8000` unless `ML_CLIENT_URL` is set.

## Troubleshooting

- **Auth fails after changing credentials:** Mongo only applies them to an empty volume. Run `docker compose down -v`.
- **Compose says a variable "is not set":** `.env` is missing values; compare it with `env.example`.
- **Web app shows `unreachable`:** ML client is down; check `docker compose logs ml-client`.
