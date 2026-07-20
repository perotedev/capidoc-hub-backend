# Tests

Unit tests only — pure logic against fakes (no real Postgres/Mongo/Redis
needed), fast enough to run on every change.

## Running

```bash
docker exec capidoc-api pip install -r requirements-dev.txt
docker exec capidoc-api sh -c "cd /app && python -m pytest tests/ -v"
```

`requirements-dev.txt` isn't baked into the image (keeps the runtime image
lean) — install it once per container, it doesn't need to survive a
recreate for local iteration since it's a one-line command.
