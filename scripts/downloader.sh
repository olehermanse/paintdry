set -e
set -x

sleep 10
while true; do
  echo "Downloader waking up"
  python3 secdb/github_downloader.py config/secrets.json ./mount-state/repos
  echo "Done downloading, starting slow modules"
  python3 modules/modgithub.py ./mount-state/modules/github/requests ./mount-state/modules/github/responses
  echo "Done processing, going to sleep"
  sleep 600
done
