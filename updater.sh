set -e
set -x

rm -rf /secdb/mount-state/modgithub
rm -rf /secdb/mount-state/modhttp
rm -rf /secdb/mount-state/moddns
find /secdb/mount-state/modules/ -name '*.json' -delete

sleep 10
psql -f schema.sql
psql -c "SELECT * FROM config;"

while true; do
  echo "SELECT * FROM config;"
  psql -c "SELECT * FROM config;"
  echo "SELECT * FROM resources;"
  psql -c "SELECT * FROM resources;"
  echo "SELECT * FROM observations;"
  psql -c "SELECT * FROM observations;"
  echo "SELECT * FROM history;"
  psql -c "SELECT * FROM history;"
  echo "SELECT * FROM changes;"
  psql -c "SELECT * FROM changes;"
  python3 -m secdb update-once
  sleep 10
done
