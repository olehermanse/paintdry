import datetime
import glob
import io
import json
import os
import tarfile

from flask import Flask, abort, send_file, send_from_directory, request
from flask.helpers import redirect
from werkzeug.security import safe_join

from paintdry.database import Database
from paintdry.lib import get_config_filename

database = Database()
# modgithub's repos in the updater's state folder (mounted in docker-compose.yml):
SBOM_REPOS = os.path.abspath("mount-state/repos/github.com")

app = Flask(__name__)


@app.route("/api/resources")
def api_resources():
    return database.get_resources()


@app.route("/api/resources/<string:id>")
def api_get_resource(id):
    result = database.get_resource(id)
    if not result:
        abort(404)
    return result


@app.route("/api/config")
def api_config():
    with open(get_config_filename(), "r") as f:
        data = json.loads(f.read())
    return data


@app.route("/api/observations")
def api_observations():
    return database.get_observations()


@app.route("/api/observations/<string:id>")
def api_get_observation(id):
    result = database.get_observation(id)
    if not result:
        abort(404)
    return result


@app.route("/api/history")
def api_history():
    return database.get_history()


@app.route("/api/history/<string:id>")
def api_get_history(id):
    result = database.get_history(id)
    if not result:
        abort(404)
    return result[0]


@app.route("/api/changes")
def api_changes():
    return database.get_changes()


@app.route("/api/changes/<string:id>")
def api_get_changes(id):
    result = database.get_changes(id)
    if not result:
        abort(404)
    return result[0]


@app.route("/api/sboms")
def api_sboms():
    sboms = []
    pattern = os.path.join(SBOM_REPOS, "*", "*", "sboms", "*", "**", "sbom.json")
    for path in sorted(glob.glob(pattern, recursive=True)):
        folder = os.path.relpath(os.path.dirname(path), SBOM_REPOS)
        org, repo, _, kind, name = folder.split("/", 4)
        mtime = os.path.getmtime(path)
        sboms.append(
            {
                "id": f"{org}/{repo}/{kind}/{name}",
                "org": org,
                "repo": repo,
                "type": {"branches": "branch", "tags": "tag"}.get(kind, kind),
                "name": name,
                # ISO, so it sorts:
                "scanned": datetime.datetime.fromtimestamp(
                    mtime, datetime.timezone.utc
                ).isoformat(),
            }
        )
    return sboms


@app.route("/api/sboms/<org>/<repo>/<kind>/<path:name>")
def api_get_sbom(org, repo, kind, name):
    # send_from_directory() 404s on missing files and paths escaping SBOM_REPOS:
    return send_from_directory(
        SBOM_REPOS,
        os.path.join(org, repo, "sboms", kind, name, "sbom.json"),
        as_attachment=True,
        download_name=f"{repo}-{name}.cdx.json".replace("/", "-"),
    )


@app.route("/api/sboms/archive", methods=["POST"])
def api_sboms_archive():
    """.tar.gz of the SBOMs in the form field ids (JSON list of /api/sboms ids)"""
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for id in json.loads(request.form["ids"]):
            org, repo, ref = id.split("/", 2)
            # None if it escapes SBOM_REPOS:
            path = safe_join(SBOM_REPOS, org, repo, "sboms", ref, "sbom.json")
            if path and os.path.isfile(path):
                tar.add(path, arcname=id + ".cdx.json")
    archive.seek(0)
    return send_file(archive, as_attachment=True, download_name="sboms.tar.gz")


@app.route("/api/search", methods=["POST"])
def api_search():
    if not request.json:
        abort(404)
    search_string = request.json.get("search", "")
    page = request.json.get("page", 1)
    return database.search(search_string, page)


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
