import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent


def _metric_names(text):
    return {m.removesuffix("_total") for m in re.findall(r"price_tracker_[a-z_]+", text)}


def test_dashboard_is_valid_json_with_panels():
    d = json.loads((ROOT / "grafana/dashboards/price-tracker.json").read_text())
    assert d["uid"]
    assert len(d["panels"]) >= 8


def test_dashboard_and_alerts_use_existing_metrics():
    known = _metric_names((ROOT / "app/metrics.py").read_text())
    used = _metric_names((ROOT / "grafana/dashboards/price-tracker.json").read_text())
    used |= _metric_names((ROOT / "prometheus/alerts.yml").read_text())
    assert used <= known, f"unknown metrics: {used - known}"
