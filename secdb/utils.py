import os
import sys
import json
import copy
import subprocess
import hashlib
import datetime
from urllib.parse import urlparse


def timestamp():
    return datetime.datetime.now().isoformat()


def sha(string):
    m = hashlib.sha256()
    m.update(string.encode("utf-8"))
    return m.hexdigest()


def merge(a, b):
    match a:
        case str():
            return b
        case int():
            return b
        case list():
            if type(b) is list:
                return a + [x for x in b if x not in a]
            else:
                return b
        case dict():
            if type(b) is dict:
                r = copy.deepcopy(a)
                for key in b:
                    if key not in a:
                        r[key] = b[key]
                    else:
                        r[key] = merge(r[key], b[key])
                return r
            else:
                return b
    assert False


def shell(command, check=False):
    if type(command) is str:
        command = command.split(" ")
    command = " ".join(command)
    command = ["bash", "-c", command]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    exit_code = result.returncode
    stdout = result.stdout.decode("utf-8")
    stderr = result.stderr.decode("utf-8")
    if check and exit_code != 0:
        print(f"Command failed: '{' '.join(command)}'")
        raise ValueError
    return (exit_code, stdout, stderr)


def ensure_folder(path):
    if os.path.isdir(path):
        return path
    if os.path.exists(path):
        sys.exit(f"'{path}' must be a folder")
    os.mkdir(path)
    return path


def ensure_json_file(path, default):
    if not path.endswith(".json"):
        sys.exit(f"'{path}' must have a .json file extension")
    if os.path.isfile(path):
        with open(path, "r") as f:
            data = f.read()
            assert data.endswith("\n")
            json.loads(data)
        return  # Assume all good
    if os.path.isdir(path):
        sys.exit(f"'{path}' must be a JSON file, not folder")
    assert not os.path.exists(path)
    with open(path, "w") as f:
        f.write(json.dumps(default, indent=2) + "\n")


class JsonFile:
    def __init__(self, path, default={}):
        self.path = path
        ensure_json_file(path, copy.deepcopy(default))
        self.autosave = True
        self.load()

    def load(self):
        with open(self.path, "r") as f:
            data = f.read()
            self._data = json.loads(data)

    def save(self, path=None):
        if not path:
            path = self.path
        with open(path, "w") as f:
            f.write(json.dumps(self._data, indent=2) + "\n")

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value
        if self.autosave:
            self.save()

    def __contains__(self, key):
        return key in self._data

    def get(self, key, default):
        if not key in self._data:
            return default
        return self._data[key]
