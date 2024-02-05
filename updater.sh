sleep 10
psql -f schema.sql
python3 lookup/update.py forever
