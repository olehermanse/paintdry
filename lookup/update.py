import os
import sys
import copy
from time import sleep

import psycopg2
import requests

from utils import JsonFile, ensure_folder, ensure_json_file, shell, sha, timestamp
from database import Database


def get_link(entry, link_name):
    for key, value in entry["links"].items():
        if value == link_name:
            return key
    raise KeyError


def is_root_url(url):
    return url.endswith((".io", ".com", ".tech"))


def is_https_url(url):
    return url.startswith("https://")


def https_to_http(url):
    assert url.startswith("https://")
    return "http://" + url[len("https://") :]


def module_http(entry):
    def get_status_code_and_location(url):
        r = requests.get(url, allow_redirects=False)
        return r.status_code, r.headers.get("Location")

    results = []
    discoveries = []

    url = entry["identifier"]
    code, redirect_location = get_status_code_and_location(url)

    entry["type"] = "status"
    entry["value"] = code
    results.append(copy.deepcopy(entry))

    if redirect_location:
        print(f"Website: {url} -> {redirect_location} ({code})")
        entry["type"] = "redirect_location"
        entry["value"] = redirect_location
        results.append(copy.deepcopy(entry))
        discoveries.append(
            {
                "module": "http",
                "identifier": redirect_location,
            }
        )
    else:
        print(f"Website: {url} -> {code}")

    if is_https_url(url) and is_root_url(url):
        http_entry = {}
        http_entry["module"] = "http"
        http_entry["identifier"] = https_to_http(url)
        discoveries.append(http_entry)

    return (results, discoveries)


class Updater:
    def __init__(self):
        self.database = Database()

    def _process(self, entry):
        match entry["module"]:
            case "http":
                return module_http(entry)
            case other:
                sys.exit(f"Target '{entry['type']}' in config not supported!")

    def process(self, entry):
        results, discoveries = self._process(entry)
        for e in results:
            self.database.upsert_resources(e)
        for e in discoveries:
            self.process(e)

    def update_config(self, entry):
        self.database.upsert_config(target)

    def update(self):
        # Read config
        config = JsonFile("config.json")

        # Setup state
        state = ensure_folder("./state")
        metadata = JsonFile(os.path.join("state", "metadata.json"))

        # Setup snapshots
        snapshots = ensure_folder(os.path.join(state, "snapshots"))

        # Prepare next snapshot
        time = timestamp()
        try:
            seq = metadata["last_update"]["seq"] + 1
        except KeyError:
            seq = 1
        snapshot_name = f"{str(seq).zfill(5)}-{time}"
        self.snapshot = ensure_folder(os.path.join(snapshots, snapshot_name))

        # Actual processing
        for target in config["targets"]:
            target = copy.deepcopy(target)
            self.update_config(target)
            self.process(target)

        # Commit snapshot
        metadata["last_update"] = {"time": time, "name": snapshot_name, "seq": seq}
        metadata.save()
        metadata.save(os.path.join(self.snapshot, "metadata.json"))


def main():
    if len(sys.argv) > 1:
        assert sys.argv[1] == "forever"
        while True:
            updater = Updater()
            updater.update()
            sleep(10)
    else:
        updater = Updater()
        updater.update()


if __name__ == "__main__":
    main()
