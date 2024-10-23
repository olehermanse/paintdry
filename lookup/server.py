import sys
import json

from flask import Flask, abort, send_file, current_app
from markupsafe import escape
import psycopg2

from database import Database

hostname = sys.argv[1]
port = int(sys.argv[2])

database = Database()

app = Flask(__name__)


@app.route("/api/search/<path:path>")
def show_user_profile(path):
    missing_http = not (path.startswith("http://") or path.startswith("https://"))
    possibilities = [path, path.strip(), "SHA=" + path]
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

    result = database.get_one_of(possibilities)
    if not result:
        abort(404)
    return current_app.response_class(
        json.dumps(result, indent=2), mimetype="application/json"
    )


@app.route("/api/list")
def list_entries():
    return sorted([key for key in database.get_observations_identifiers()])


@app.route("/")
@app.route("/<path:path>")
def hello_world(path=None):
    return send_file("index.html")


def main():
    app.run(host=hostname, port=port)


if __name__ == "__main__":
    main()
