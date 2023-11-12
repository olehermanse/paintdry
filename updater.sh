sleep 10
psql -f schema.sql
python update.py forever
