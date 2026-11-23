![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)

# Containerized App Exercise

Build a containerized app that uses machine learning. See [instructions](./instructions.md) for details.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- Python 3.12+ (only for running a service outside Docker)

## Configuration

```bash
cp env.example .env
```

| Variable | Purpose |
|---|---|
| `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD` | Credentials for the MongoDB container |
| `MONGO_DB` | Database name |
| `MONGO_URI` | URI used when running a service directly on your machine |
| `WEB_APP_PORT` / `ML_CLIENT_PORT` | Host ports |
| `ML_CLIENT_URL` | Where the web app finds the ML client (default `http://localhost:8000`) |

## Running

### 1. Start MongoDB

```bash
docker run -d --name focuscam-mongo -p 27017:27017 \
  -v focuscam-mongo-data:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secret \
  mongo
```

If port 27017 is already in use, change the host side of `-p` (for example `27018:27017`) and use that port in the URIs below. The named volume keeps data across container restarts and removals.

### 2. Run the machine learning client

**In Docker:**

```bash
cd machine-learning-client
docker build -t focuscam-ml-client .
docker run -d --name ml-client -p 8000:8000 \
  -e MONGO_URI="mongodb://admin:secret@host.docker.internal:27017/focuscam?authSource=admin" \
  focuscam-ml-client
```
**Locally:**

```bash
cd machine-learning-client
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

### 3. Run the web app

**In Docker:**

```bash
cd web-app
docker build -t focuscam-web-app .
docker run -d --name web-app -p 5001:5000 \
  -e MONGO_URI="mongodb://admin:secret@host.docker.internal:27017/focuscam?authSource=admin" \
  -e ML_CLIENT_URL="http://host.docker.internal:8000" \
  focuscam-web-app
```
**Locally:**

```bash
cd web-app
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```
### 4. Verify

```bash
curl localhost:8000/health
# {"status":"ok"}

docker exec focuscam-mongo mongosh -u admin -p secret \
  --authenticationDatabase admin focuscam --quiet \
  --eval 'db.getCollection("hello").find().toArray()'
```

### Cleanup

```bash
docker rm -f web-app ml-client focuscam-mongo
docker volume rm focuscam-mongo-data   # also deletes the stored data
