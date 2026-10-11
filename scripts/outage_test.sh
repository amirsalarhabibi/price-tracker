#!/usr/bin/env bash
# Simulates an upstream outage by dropping the container's outgoing traffic only.
# The host network and Docker's own network are not touched.
set -u
get() { docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8000/prices/usd/latest').read().decode())"; }
age() { docker compose exec -T api python -c "import urllib.request,json; print(json.load(urllib.request.urlopen('http://127.0.0.1:8000/prices/usd/latest'))['age_seconds'])" 2>/dev/null; }
sudo -v
trap 'sudo iptables -D DOCKER-USER -j DROP 2>/dev/null' EXIT
echo "--- ip_forward = $(cat /proc/sys/net/ipv4/ip_forward)  (should be 1)"
docker compose up -d
echo "--- waiting 70s for the first prices"; sleep 70
echo "--- BEFORE outage:"; get
sudo iptables -I DOCKER-USER -j DROP || { echo "could not add the block rule"; docker compose down; exit 1; }
echo "--- outage ON (container cannot reach the internet), waiting 130s"; sleep 130
echo "--- DURING outage:"; get
echo "--- from host (should still work):"; curl -s --max-time 5 localhost:8000/health || echo "localhost:8000 not reachable"; echo
sudo iptables -D DOCKER-USER -j DROP
echo "--- outage OFF, waiting for recovery (up to 150s)"
r=0; ok=0
while [ $r -lt 150 ]; do
  a=$(age)
  if [ -n "$a" ] && [ "$a" -lt 90 ]; then ok=1; break; fi
  r=$((r+10)); sleep 10
done
if [ $ok -eq 1 ]; then echo "--- RECOVERED after about ${r}s"; else echo "--- NOT recovered after ${r}s"; fi
get
echo "--- last logs:"; docker compose logs --tail 10 api
if [ $ok -eq 0 ]; then
  echo "--- DNS inside container:"
  docker compose exec -T api python -c "import socket; print(socket.gethostbyname('api.gold-api.com'))" 2>&1 | tail -1
  echo "--- HTTPS inside container:"
  docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('https://api.gold-api.com/price/XAU', timeout=6).status)" 2>&1 | tail -1
fi
docker compose down
