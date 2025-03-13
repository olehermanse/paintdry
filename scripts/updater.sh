#!/bin/bash
set -e
set -x

find /secdb/mount-state/modules/ -name '*.json' -delete || true

sleep 10
psql -f schema.sql

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
  sleep 10
done
