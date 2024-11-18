set -e
set -x

sleep 10
while true; do
  echo "Downloader waking up"
  python3 secdb/download_repos.py config/secrets.json ./mount-state/repos
  echo "Downloader going to sleep"
  sleep 600
done
