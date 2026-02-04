#!/bin/bash
set -e
set -x

echo "Waiting for database to be ready and applying schema..."
until psql -f schema.sql; do
  echo "Schema application failed, retrying in 5 seconds..."
  sleep 5
done
echo "Schema successfully applied!"

while true; do
  echo "Deleting stale requests"
  find /paintdry/mount-state/modules/ -name '*.json' -delete || true
  python3 paintdry/config_requests.py
  python3 paintdry/resource_requests.py
  python3 paintdry/run_modules.py
  python3 paintdry/process_responses.py
  python3 paintdry/run_modules.py
  python3 paintdry/process_responses.py
  sleep 60
  echo "Updater waking up"
done
