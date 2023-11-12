import os
import sys
import copy
from time import sleep

import psycopg2

from utils import JsonFile, ensure_folder, ensure_json_file, shell, sha, timestamp
from database import Database


def get_link(entry, link_name):
    for key, value in entry["links"].items():
        if value == link_name:
            return key
    raise KeyError


def module_website_single(database, snapshot, entry):
    print(f'Website: {entry["url"]}')
    database.upsert_entry(entry["url"])
    # entry = database.insert_entry(entry["url"], entry)
    # target_folder = os.path.join(snapshot, get_link(entry, "string_hash"))
    # ensure_folder(target_folder)
    # destination = os.path.join(target_folder, "index.html")
    # r, out, err = shell(f'curl {entry["url"]} -o {destination}')
    # r, out, err = shell(f'cd {target_folder} && prettier --no-color index.html')
    # if err:
    #     updater.database.add_alert(entry, error=err)
    # elif r != 0:
    #     sys.exit("Unknown error")


def module_git_repo(database, snapshot, entry):
    print(f'Git repo: {entry["url"]}')
    database.upsert_entry(entry["url"], entry)


class Updater:
    def __init__(self):
        self.database = Database()

    def process(self, entry):
        match entry["type"]:
            case "website_single":
                module_website_single(self.database, self.snapshot, entry)
            case "git_repo":
                module_git_repo(self.database, self.snapshot, entry)
            case other:
                sys.exit(f"Target '{entry['type']}' in config not supported!")

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
