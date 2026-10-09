import random

BASE = {"usd": 60000, "gold": 3000000}  # fake numbers

def fetch_price(asset: str) -> int:
    if asset not in BASE:
        raise ValueError(f"unknown asset: {asset}")
    return round(BASE[asset] * random.uniform(0.98, 1.02))
