#!/bin/bash
set -e
set -x

find /secdb/mount-state/modules/ -name '*.json' -delete || true

echo "Waiting for database to be ready and applying schema..."
until psql -f schema.sql; do
  echo "Schema application failed, retrying in 5 seconds..."
  sleep 5
done
echo "Schema successfully applied!"

while true; do
  echo "SELECT * FROM resources LIMIT 5;"
  psql -c "SELECT * FROM resources LIMIT 5;"
  echo "SELECT * FROM observations LIMIT 5;"
  psql -c "SELECT * FROM observations LIMIT 5;"
  echo "SELECT * FROM history LIMIT 5;"
  psql -c "SELECT * FROM history LIMIT 5;"
  echo "SELECT * FROM changes LIMIT 5;"
  psql -c "SELECT * FROM changes LIMIT 5;"
  python3 -m secdb update-once
  sleep 60
done
