sleep 10
psql -f schema.sql
python lookup/update.py forever
