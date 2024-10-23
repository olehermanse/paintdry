
sleep 10
psql -f schema.sql
while true; do
  echo "SELECT * FROM config;"
  psql -c "SELECT * FROM config;"
  echo "SELECT * FROM resources;"
  psql -c "SELECT * FROM resources;"
  echo "SELECT * FROM observations;"
  psql -c "SELECT * FROM observations;"
  echo "SELECT * FROM history;"
  psql -c "SELECT * FROM history;"
  echo "SELECT * FROM events;"
  psql -c "SELECT * FROM events;"
  python3 -m lookup update-once
  sleep 10
done
