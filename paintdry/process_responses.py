import os
import json
import datetime
import pathlib

from paintdry.utils import JsonFile, sha
from paintdry.database import Database
from paintdry.lib import (
    ModuleRequest,
    Discovery,
    Observation,
    Resource,
    Change,
    get_config_filename,
)


def now() -> int:
    return int(datetime.datetime.now().timestamp())


def dump_json_atomic(filename, data):
    string = json.dumps(data) + "\n"
    tmpfile = filename + ".tmp"
    with open(tmpfile, "w") as f:
        f.write(string)
    os.replace(tmpfile, filename)


def write_requests(folder: str, requests: list[ModuleRequest]):
    data = json.loads(json.dumps(requests))
    for element in data:
        del element["timestamp"]
    filename = sha(json.dumps(data))
    path = folder + "/" + filename + ".json"
    if os.path.exists(path):
        return
    dump_json_atomic(path, requests)


def response_to_discovery(response: dict) -> Discovery:
    data = {**response}
    assert data["operation"] == "discovery"
    del data["operation"]
    return Discovery(**data)


def response_to_observation(response: dict) -> Observation:
    data = {**response}
    assert data["operation"] == "observation"
    del data["operation"]
    return Observation(**data)


def response_to_change(response: dict) -> Change:
    data = {**response}
    assert data["operation"] == "change"
    del data["operation"]
    return Change(**data)


class ResponseProcessor:
    def __init__(self):
        self.database = Database()
        self.discovery_backlog = []

    def process_discovery(self, source_module: str, discovery: Discovery):
        if discovery.module != source_module:
            print(
                f"Discovery: {discovery.resource} for {discovery.module} suggested by {source_module}"
            )
            self.discovery_backlog.append(discovery)
            return
        print(f"Discovery: {discovery.resource} accepted by {source_module}")
        self.database.upsert_resource(
            Resource.from_discovery(discovery), discovery.source
        )

    def process_change(self, change: Change):
        self.database.update_change(change)

    def process_response(self, source_module: str, response: dict):
        if response["operation"] == "observation":
            observation = response_to_observation(response)
            self.database.upsert_observations(observation)
            return
        if response["operation"] == "discovery":
            discovery = response_to_discovery(response)
            self.process_discovery(source_module, discovery)
            return
        assert response["operation"] == "change"
        change = response_to_change(response)
        self.process_change(change)

    def process_module_responses(self, module_name: str):
        output_folder = f"./mount-state/modules/{module_name}/responses"
        if not os.path.isdir(output_folder):
            return
        print(f"Processing responses for {module_name}")
        n = 0
        with os.scandir(output_folder) as it:
            for entry in it:
                if not entry.is_file() or not entry.name.endswith(".json"):
                    continue
                n += 1
                with open(entry.path, "r") as f:
                    data = json.loads(f.read())
                assert type(data) is list
                for response in data:
                    self.process_response(module_name, response)
                print("Done processing response, deleting: " + entry.path)
                os.unlink(entry.path)
        print(f"Done processing {n} responses for {module_name}")

    def process_discovery_backlog(self):
        if not self.discovery_backlog:
            return
        print(f"Processing {len(self.discovery_backlog)} discoveries in backlog")
        modules = {}
        for discovery in self.discovery_backlog:
            request = ModuleRequest(
                operation="discovery",
                resource=discovery.resource,
                module=discovery.module,
                source=discovery.source,
                timestamp=now(),
            )
            if discovery.module not in modules:
                modules[discovery.module] = []
            modules[discovery.module].append(request)

        for name, requests in modules.items():
            input_folder = f"./mount-state/modules/{name}/requests"
            pathlib.Path(input_folder).mkdir(parents=True, exist_ok=True)
            write_requests(input_folder, requests)
            print(f"Wrote {len(requests)} discovery requests for {name}")
        self.discovery_backlog = []


def process_responses():
    config = JsonFile(get_config_filename())
    processor = ResponseProcessor()

    for module_name in config["modules"]:
        processor.process_module_responses(module_name)

    processor.process_discovery_backlog()


if __name__ == "__main__":
    process_responses()
