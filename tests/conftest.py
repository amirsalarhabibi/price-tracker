import os

# Set before any test module imports the app: offline tests, no poller, no refresh cache.
os.environ["DB_PATH"] = "/tmp/test_prices.db"
os.environ["USE_FAKE_SOURCES"] = "1"
os.environ["DISABLE_POLLER"] = "1"
os.environ["REFRESH_MIN_INTERVAL"] = "0"
