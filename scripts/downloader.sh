#!/bin/bash
set -e
set -x

sleep 10
while true; do
  echo "Downloader waking up"
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 10
  python3 secdb/github_downloader.py config/secrets.json ./mount-state/repos
  echo "Done downloading, running modules"
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  sleep 60
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
done
