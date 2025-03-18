#!/bin/bash
set -e
set -x

sleep 10
while true; do
  echo "Downloader waking up"
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses ./mount-state/
  sleep 10
  python3 secdb/github_downloader.py config/secrets.json ./mount-state/repos ./mount-state/
  echo "Done downloading, running modules"
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses ./mount-state/
  sleep 60
done
