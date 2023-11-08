import sys
import json

from flask import Flask, abort, send_file
from markupsafe import escape
import psycopg2

hostname = sys.argv[1]
port = int(sys.argv[2])

with open("state/database.json", "r") as f:
    database = json.loads(f.read())

app = Flask(__name__)

@app.route('/api/search/<path:path>')
def show_user_profile(path):
    try:
        conn = psycopg2.connect("host='postgres' dbname='postgres' user='postgres' host='postgres' password='postgres'")
        print("Connected to PG")
    except:
        print("I am unable to connect to the database")
    missing_http = not (path.startswith("http://") or path.startswith("https://"))
    possibilities = [
        path,
        path.strip(),
        "SHA=" + path
    ]
    if missing_http:
        possibilities.append("https://" + path)
        possibilities.append("https://" + path + "/")
        possibilities.append("http://" + path)
        possibilities.append("http://" + path + "/")
    while path.endswith("/"):
        path = path[0:-1]
        possibilities.append(path)
        if missing_http:
            possibilities.append("http://" + path)
            possibilities.append("https://" + path)
    if path.endswith(".git"):
        path = path[0:-4]
        possibilities.append(path)
        if missing_http:
            possibilities.append("http://" + path)
            possibilities.append("https://" + path)
    for x in possibilities:
        if x in database["index"]:
            return database["index"][x]
    abort(404)

@app.route('/api/list')
def list_entries():
    return sorted([key for key in database["index"]])

@app.route('/')
@app.route('/<path:path>')
def hello_world(path=None):
    try:
        conn = psycopg2.connect("host='postgres' dbname='postgres' user='postgres' host='postgres' password='postgres'")
        print("Connected to PG")
    except:
        print("I am unable to connect to the database")
    return send_file("index.html")

def main():
    app.run(host=hostname, port=port)

if __name__ == '__main__':
    main()
