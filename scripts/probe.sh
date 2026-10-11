#!/usr/bin/env bash
# usage: ./scripts/probe.sh URL [URL...]
for u in "$@"; do
  out=$(mktemp)
  res=$(curl -s -o "$out" -w "%{http_code} %{time_total}s" --max-time 8 -A "Mozilla/5.0" "$u")
  rc=$?
  echo "== $u -> $res (curl exit=$rc)"
  [ -s "$out" ] && head -c 300 "$out"
  echo
  rm -f "$out"
done
