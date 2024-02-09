sleep 10
psql -f schema.sql
echo "CONFIG:"
psql -c "SELECT * FROM config;"
echo "RESOURCES:"
psql -c "SELECT * FROM resources;"
echo "HISTORY:"
psql -c "SELECT * FROM history;"
echo "EVENTS:"
psql -c "SELECT * FROM events;"
python3 lookup/update.py forever
