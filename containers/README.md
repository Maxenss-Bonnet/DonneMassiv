# Containers

This folder is a minimal, hands-on example to show how Docker and Docker Compose work together.
For the full teaching material, use `en/practical6/practical6.ipynb`.

## What's Here
- `acquisition/`: a tiny Python container example.
- `docker-compose.yaml`: Compose file that builds the acquisition image.

## Quick Start
From `containers/`:

```bash
docker compose up --build
```

Stop and remove containers:

```bash
docker compose down
```

## Tips
- Rebuild when you change `containers/acquisition/acquisition.py`.
- Use `docker compose logs -f` to see container output.
