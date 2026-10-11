# Price Tracker

![CI](https://github.com/amirsalarhabibi/price-tracker/actions/workflows/ci.yml/badge.svg)

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
- [x] Real price sources (Nobitex USDT, world gold ounce)
- [ ] Telegram alerts
- [ ] Prometheus and Grafana monitoring

## How it works

- Prices are collected from several sources in parallel, each with a timeout. A failing source is skipped instead of breaking the request.
- Sources fed by the same upstream share a *group*. Confidence (`low` / `medium` / `high`) depends on the number of independent groups, not on the number of sources.
- A background task polls every 60 seconds (`POLL_INTERVAL`) and stores each result with its confidence.
- `GET /prices/{asset}/latest` returns the age of the data and a `stale` flag, so old data is never presented as fresh.
- The USD price is the USDT price on an Iranian exchange, used as a proxy. 18k gold per gram is an *estimate* derived from the world ounce price and the USD price, and is marked `estimated: true`.
