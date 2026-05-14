#!/usr/bin/env bash
# Streams output with timestamps — use as ExecStart in a test service
for i in $(seq 1 20); do
  echo "[$(date '+%H:%M:%S')] line $i — $(tr -dc 'a-z0-9 ' </dev/urandom | head -c 40)"
  sleep 0.5
done
echo "[$(date '+%H:%M:%S')] done."
