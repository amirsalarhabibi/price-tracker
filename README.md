# Price Tracker

A small FastAPI service that records USD and gold prices and exposes their history.
Built as a DevOps portfolio project: Docker, GitHub Actions CI, and (coming next) monitoring.

## Run locally

```bash
docker compose up --build
```

Then open http://127.0.0.1:8000/docs

## Endpoints

- `GET /health`: service status
- `POST /prices/{asset}/refresh`: fetch and store the latest price (`usd`, `gold`)
- `GET /prices/{asset}/history`: stored price history

## Tests

```bash
pip install -r requirements.txt
python -m pytest
```

## Roadmap

- [x] API + SQLite storage
- [x] Dockerfile and docker-compose
- [x] CI with GitHub Actions
- [ ] Real price source
- [ ] Telegram alerts
- [ ] Prometheus and Grafana monitoring
