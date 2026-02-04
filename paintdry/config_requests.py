import os
import json
import datetime
import pathlib

from paintdry.utils import JsonFile, sha
from paintdry.lib import ModuleRequest, get_config_filename


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


def ensure_module_folder(name: str) -> str:
    module_folder = f"./mount-state/modules/{name}"
    input_folder = f"{module_folder}/requests"
    output_folder = f"{module_folder}/responses"
    pathlib.Path(input_folder).mkdir(parents=True, exist_ok=True)
    pathlib.Path(output_folder).mkdir(parents=True, exist_ok=True)
    return input_folder


def process_config():
    config = JsonFile(get_config_filename())

    for target in config["targets"]:
        for module in target["modules"]:
            for resource in target["resources"]:
                print(f"Processing config: {module} {resource}")
                input_folder = ensure_module_folder(module)
                request = ModuleRequest(
                    operation="discovery",
                    resource=resource,
                    module=module,
                    source="config.json",
                    timestamp=now(),
                )
                write_requests(input_folder, [request])


if __name__ == "__main__":
    process_config()
