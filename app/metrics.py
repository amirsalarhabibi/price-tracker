from prometheus_client import CollectorRegistry
from prometheus_client.core import CounterMetricFamily, GaugeMetricFamily

from app import db, sources

REGISTRY = CollectorRegistry()


class TrackerCollector:
    """Builds the metrics when Prometheus scrapes, from the source stats and the database."""

    def collect(self):
        snap = sources.snapshot()

        up = GaugeMetricFamily(
            "price_tracker_source_up", "1 if the last attempt on this source worked", labels=["source"]
        )
        last_ok = GaugeMetricFamily(
            "price_tracker_source_last_success_timestamp_seconds",
            "Unix time of the last successful fetch",
            labels=["source"],
        )
        attempts = CounterMetricFamily(
            "price_tracker_source_requests", "Fetch attempts per source", labels=["source"]
        )
        failures = CounterMetricFamily(
            "price_tracker_source_failures",
            "Failed fetches per source and error type",
            labels=["source", "error"],
        )
        for name, s in snap.items():
            if s["up"] is not None:
                up.add_metric([name], 1 if s["up"] else 0)
            if s["last_success_ts"] is not None:
                last_ok.add_metric([name], s["last_success_ts"])
            attempts.add_metric([name], s["attempts"])
            for err, n in s["failures"].items():
                failures.add_metric([name, err], n)
        yield up
        yield last_ok
        yield attempts
        yield failures

        price = GaugeMetricFamily(
            "price_tracker_price", "Latest stored price (toman)", labels=["asset"]
        )
        age = GaugeMetricFamily(
            "price_tracker_price_age_seconds", "Age of the latest stored price", labels=["asset"]
        )
        groups = GaugeMetricFamily(
            "price_tracker_groups_ok", "Independent source groups behind the latest price", labels=["asset"]
        )
        try:
            with db.get_conn() as c:
                rows = c.execute(
                    "SELECT asset, price, groups_ok, "
                    "CAST(strftime('%s','now') - strftime('%s', created_at) AS INTEGER) AS age "
                    "FROM prices WHERE id IN (SELECT MAX(id) FROM prices GROUP BY asset)"
                ).fetchall()
        except Exception:
            rows = []
        for r in rows:
            price.add_metric([r["asset"]], r["price"])
            age.add_metric([r["asset"]], r["age"])
            groups.add_metric([r["asset"]], r["groups_ok"])
        yield price
        yield age
        yield groups


REGISTRY.register(TrackerCollector())
