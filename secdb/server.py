import json

from flask import Flask, abort, send_from_directory, request
from flask.helpers import redirect

from secdb.database import Database

database = Database()

app = Flask(__name__)


@app.route("/api/resources")
def api_resources():
    return database.get_resources()


@app.route("/api/resources/<int:id>")
def api_get_resource(id):
    result = database.get_resource(id)
    if not result:
        abort(404)
    return result


@app.route("/api/config")
def api_config():
    with open("./config/config.json", "r") as f:
        data = json.loads(f.read())
    return data


@app.route("/api/observations")
def api_observations():
    return database.get_observations()


@app.route("/api/observations/<int:id>")
def api_get_observation(id):
    result = database.get_observation(id)
    if not result:
        abort(404)
    return result


@app.route("/api/history")
def api_history():
    return database.get_history()


@app.route("/api/history/<int:id>")
def api_get_history(id):
    result = database.get_history(id)
    if not result:
        abort(404)
    return result[0]


@app.route("/api/changes")
def api_changes():
    return database.get_changes()


@app.route("/api/changes/<int:id>")
def api_get_changes(id):
    result = database.get_changes(id)
    if not result:
        abort(404)
    return result[0]


@app.route("/api/search", methods=["POST"])
def api_search():
    search_string = request.json.get("search", "")
    return database.search(search_string)


@app.route("/")
def redirect_to_ui():
    return redirect("/ui/")


@app.route("/ui/")
@app.route("/ui/<path:path>")
def ui(path=None):
    return send_from_directory("dist", "index.html")


@app.route("/<path:path>")
def index(path=None):
    if not path or path == "/":
        path = "index.html"
    return send_from_directory("dist", path)


def start_server(host, port):
    app.run(host=host, port=port)
