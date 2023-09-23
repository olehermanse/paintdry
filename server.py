import sys
import json

from flask import Flask, abort, send_file
from markupsafe import escape

hostname = sys.argv[1]
port = int(sys.argv[2])

with open("state/database.json", "r") as f:
    database = json.loads(f.read())

app = Flask(__name__)

@app.route('/api/lookup/<path:path>')
def show_user_profile(path):
    if path not in database["index"]:
        abort(404)
    return database["index"][path]

@app.route('/')
@app.route('/<path:path>')
def hello_world(path=None):
    return send_file("index.html")

def main():
    app.run(host=hostname, port=port)

if __name__ == '__main__':
    main()
