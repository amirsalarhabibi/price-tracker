#!/usr/bin/env bash
# usage: ./scripts/probe.sh URL [URL...]
for u in "$@"; do
  res=$(curl -s -o /tmp/probe.out -w "%{http_code} %{time_total}s" --max-time 8 -A "Mozilla/5.0" "$u")
  echo "== $u -> $res"
  head -c 300 /tmp/probe.out
  echo
done
