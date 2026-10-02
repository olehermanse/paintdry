import os
import sys
import json
import copy
import subprocess
import shutil
import hashlib
import datetime


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


def mkdir(path):
    os.makedirs(path, exist_ok=True)


def rm_rf(path):
    print("RM: " + path)
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.remove(path)


def cmd(command, token=None, fail_ok=False):
    def mask(s):
        return s.replace(token, "TOKEN") if token else s

    print("CMD: " + mask(command))
    r = subprocess.run(command, shell=True, capture_output=True, text=True)
    if r.stdout:
        print(mask(r.stdout), end="")
    if r.stderr:
        print(mask(r.stderr), end="", file=sys.stderr)
    if r.returncode != 0 and not fail_ok:
        print(f"Warning: Command exited with code {r.returncode}")
    return r


def user_error(message):
    print("Error: " + message)
    sys.exit(1)


def env_var(key):
    r = os.getenv(key)
    if not r:
        user_error("Environment variable missing: " + key)
    return r
