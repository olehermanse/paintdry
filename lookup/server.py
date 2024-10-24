import sys
import json

from flask import Flask, abort, send_file, current_app, send_from_directory
from flask.helpers import redirect
import psycopg2

from lookup.database import Database


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
    return sorted([key for key in database.get_observations_resources()])

@app.route("/api/resources")
def api_resources():
    return database.get_resources()

@app.route("/")
def redirect_to_ui():
    return redirect("/ui/")


@app.route("/ui/")
@app.route("/ui/<path:path>")
def ui(path=None):
    return send_from_directory('dist', "index.html")


@app.route("/<path:path>")
def index(path=None):
    if not path or path == "/":
        path = "index.html"
    return send_from_directory('dist', path)


def start_server(host, port):
    app.run(host=host, port=port)
