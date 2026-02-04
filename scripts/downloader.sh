#!/bin/bash
set -e
set -x

sleep 10
while true; do
  python3 paintdry/github_downloader.py config/secrets.json ./mount-state/repos ./mount-state/
  sleep 60
  echo "Downloader waking up"
done
