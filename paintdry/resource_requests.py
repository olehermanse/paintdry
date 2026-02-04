import os
import json
import datetime
import pathlib

from paintdry.utils import sha
from paintdry.database import Database
from paintdry.lib import ModuleRequest


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


def generate_resource_requests():
    database = Database()
    modules = {}

    for resource in database.get_resources():
        module = resource.module
        source = resource["source"] or ""
        timestamp = now()

        if module not in modules:
            modules[module] = []

        print(f"Generating requests for {module}: {resource.resource}")

        modules[module].append(
            ModuleRequest(
                operation="discovery",
                resource=resource.resource,
                module=module,
                source=source,
                timestamp=timestamp,
            )
        )
        modules[module].append(
            ModuleRequest(
                operation="observation",
                resource=resource.resource,
                module=module,
                timestamp=timestamp,
            )
        )

    for module, requests in modules.items():
        input_folder = f"./mount-state/modules/{module}/requests"
        pathlib.Path(input_folder).mkdir(parents=True, exist_ok=True)
        write_requests(input_folder, requests)
        print(f"Wrote {len(requests)} requests for {module}")


if __name__ == "__main__":
    generate_resource_requests()
