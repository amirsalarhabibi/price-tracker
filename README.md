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

## Outage behavior

`scripts/outage_test.sh` blocks the container's outgoing traffic for about two minutes (needs sudo, uses the iptables `DOCKER-USER` chain). While blocked, the API keeps serving the last stored price together with its `age_seconds`. After the block is removed, polling resumes on its own (about 20 seconds in the last run).

## Monitoring

- `GET /metrics` exposes Prometheus metrics: `price_tracker_price`, `price_tracker_price_age_seconds`, `price_tracker_groups_ok`, `price_tracker_source_up`, `price_tracker_source_last_success_timestamp_seconds`, `price_tracker_source_requests_total` and `price_tracker_source_failures_total{error=...}`.
- `GET /sources` returns the same per-source status as JSON.
- Every failure is classified (`dns`, `timeout`, `tls`, `http_error`, `connection`, `bad_response`, `other`), which makes it possible to tell a blocked source apart from one that changed its response format.
- Source counters live in memory and reset when the service restarts.

## Monitoring stack

`docker compose up --build` also starts Prometheus and Grafana (bound to localhost only).

- Grafana: http://localhost:3000 (user `admin`, password `admin` unless `GRAFANA_PASSWORD` is set). The "Price Tracker" dashboard is provisioned automatically.
- Prometheus: http://localhost:9090 (targets at `/targets`, alert rules at `/alerts`).
- Alert rules: `TrackerDown` (API cannot be scraped), `PriceStale` (price older than 15 minutes), `SourceDown` (a source failing for 3 minutes).
- A test checks that the dashboard and the alert rules only use metrics the app really exports.
