![Lint-free](https://github.com/nyu-software-engineering/containerized-app-exercise/actions/workflows/lint.yml/badge.svg)

# Containerized App Exercise

Build a containerized app that uses machine learning. See [instructions](./instructions.md) for details.

## Configuration

Copy the example file and edit it if needed. `.env` is git-ignored.

```bash
cp env.example .env
```

| Variable | Purpose |
|---|---|
| `MONGO_INITDB_ROOT_USERNAME` / `MONGO_INITDB_ROOT_PASSWORD` | Credentials for the MongoDB container |
| `MONGO_DB` | Database name |
| `MONGO_URI` | URI used when running a service directly on your machine |
| `WEB_APP_PORT` / `ML_CLIENT_PORT` | Host ports |

## Running

### 1. Start MongoDB

```bash
docker run -d --name focuscam-mongo -p 27017:27017 \
  -v focuscam-mongo-data:/data/db \
  -e MONGO_INITDB_ROOT_USERNAME=admin \
  -e MONGO_INITDB_ROOT_PASSWORD=secret \
  mongo
```

If port 27017 is already in use, change the host side of `-p` (for example `27018:27017`) and use that port in `MONGO_URI`. The named volume keeps data across container restarts and removals.

### 2. Run the machine learning client

**In Docker:**

```bash
cd machine-learning-client
docker build -t focuscam-ml-client .
docker run -d --name ml-client -p 8000:8000 \
  -e MONGO_URI="mongodb://admin:secret@host.docker.internal:27017/focuscam?authSource=admin" \
  focuscam-ml-client
```

Inside a container, `localhost` refers to the container itself, so the URI uses `host.docker.internal` to reach MongoDB on the host. On Linux, add `--add-host=host.docker.internal:host-gateway`.

**Locally:**

```bash
cd machine-learning-client
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.main
```

The local run reads `MONGO_URI` from the `.env` file at the repo root.

### 3. Verify

```bash
curl localhost:8000/health
# {"status":"ok"}

docker exec focuscam-mongo mongosh -u admin -p secret \
  --authenticationDatabase admin focuscam --quiet \
  --eval 'db.getCollection("hello").find().toArray()'
```

On startup the client inserts one document into the `hello` collection, so the second command should list it.

### Cleanup

```bash
docker rm -f ml-client focuscam-mongo
docker volume rm focuscam-mongo-data   # also deletes the stored data
```
