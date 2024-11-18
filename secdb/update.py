import os
import sys
import json
import datetime
import pathlib
from time import sleep
from subprocess import Popen, PIPE, STDOUT

from secdb.utils import JsonFile, ensure_folder, timestamp
from secdb.database import Database
from secdb.lib import (
    ModuleRequest,
    ModuleResponse,
    clear_get_cache,
    Discovery,
    Observation,
    Resource,
    ConfigTarget,
)


def now() -> int:
    return int(datetime.datetime.now().timestamp())

def dump_json_atomic(filename, data):
    string = json.dumps(data) + "\n"
    tmpfile = filename + ".tmp"
    with open(tmpfile, "w") as f:
        f.write(string)
    os.replace(tmpfile, filename)

def response_to_discovery(response: ModuleResponse) -> Discovery:
    data = {**response}
    assert data["operation"] == "discovery"
    del data["operation"]
    return Discovery(**data)


def response_to_observation(response: ModuleResponse) -> Observation:
    data = {**response}
    assert data["operation"] == "observation"
    del data["operation"]
    return Observation(**data)

class Module:
    def __init__(self, name, command):
        self.name = name
        print(f"Starting '{name}' module")
        assert not " " in name
        assert not "/" in name
        assert not "," in name
        assert not "." in name
        assert not "'" in name
        assert not "\"" in name
        assert not "\n" in name
        module_folder = f"/secdb/mount-state/modules/{name}"
        input_folder = f"{module_folder}/requests"
        output_folder = f"{module_folder}/responses"
        pathlib.Path(input_folder).mkdir(parents=True, exist_ok=True)
        pathlib.Path(output_folder).mkdir(parents=True, exist_ok=True)
        command = f"cd '{module_folder}' && {command} '{input_folder}' '{output_folder}'"
        self._command = command
        self._module_folder = module_folder
        self._input_folder = input_folder
        self._output_folder = output_folder
        self._process = None
        self._request_backlog = []
        self._request_counter = 0

    def _wait_process(self):
        if self._process is None:
            return

        (out, err) = self._process.communicate()
        out = out.strip()
        if out:
            print(f"Stdout from {self.name} module:")
            print(out)
        if err:
            print(f"Stderr from {self.name} module:")
            print(err)

        r = self._process.wait()
        if r != 0:
            print(f"Module {self.name} exited with error: {r}")

        self._process = None

    def process_responses(self, callback):
        with os.scandir(self._output_folder) as it:
            for entry in it:
                if not entry.is_file() or not entry.name.endswith(".json"):
                    continue
                with open(entry.path, "r") as f:
                    data = json.loads(f.read())
                assert type(data) is list
                for response in data:
                    callback(response)
                print("Done processing request, deleting: " + entry.path)
                os.unlink(entry.path)

    def process_all_responses(self, callback):
        self._wait_process() # Finish current process
        self._maybe_start()  # Start new one if more requests
        self._wait_process() # Finish last one
        self.process_responses(callback)

    def _start_process(self):
        self._wait_process()
        self._process = Popen(
            self._command,
            shell=True,
            text=True,
            encoding="utf-8",
            stdin=PIPE,
            stdout=PIPE,
            stderr=STDOUT,
        )

    def _next_filename(self):
        name = f"{self._input_folder}/{now()}-{self._request_counter}.json"
        self._request_counter += 1
        return name

    def _dump_backlog(self):
        self.write_requests(self._request_backlog)
        self._request_backlog = []

    def _maybe_start(self):
        # TODO check if process already exited so we can start another
        if self._process:
            return
        if len(self._request_backlog) == 0:
            return
        self._dump_backlog()
        self._start_process()

    def write_requests(self, requests):
        filename = self._next_filename()
        dump_json_atomic(filename, requests)

    def send_requests(self, requests: list[ModuleRequest]):
        self._request_backlog.extend(requests)
        self._maybe_start()

class Updater:
    def __init__(self):
        self.database = Database()
        self.cache = {}
        self.modules = {}
        self.discovery_backlog = []

    def send_requests(self, name: str, requests: list[ModuleRequest]):
        module = self.get_module(name)
        module.send_requests(requests)

    def get_module(self, module: str):
        if not module in self.modules:
            config = JsonFile("config/config.json")
            command = config['modules'][module]['command']
            self.modules[module] = Module(module, command)
        return self.modules[module]

    def receive_responses(self, module: str) -> list[ModuleResponse]:
        process = self.get_module(module)
        responses: list[ModuleResponse] = []
        while True:
            response = process.stdout.readline().strip()
            if not response:
                break
            try:
                data = json.loads(response)
            except:
                print("Failed to parse JSON;")
                print(response)
                continue
            responses.append(ModuleResponse.convert(data))
        return responses

    def process_discovery_backlog(self):
        modules = {}
        for discovery in self.discovery_backlog:
            request = ModuleRequest(
                operation="discovery",
                resource=discovery.resource,
                module=discovery.module,
                source=discovery.source,
                timestamp=now(),
            )
            if not discovery.module in modules:
                modules[discovery.module] = []
            modules[discovery.module].append(request)

        for name, requests in modules.items():
            module = self.get_module(name)
            module.write_requests(requests)
        self.discovery_backlog = []

    def send_request_for_resource(self, resource: Resource, module: str):
        print(f"Sending requests to '{module}' module for '{resource.resource}'")
        source = resource["source"]
        if not source:
            source = ""  # TODO FIXME
        requests = []
        timestamp = now()
        requests.append(ModuleRequest(
            operation="discovery",
            resource=resource.resource,
            module=module,
            source=source,
            timestamp=timestamp,
        ))
        requests.append(ModuleRequest(
            operation="observation",
            resource=resource.resource,
            module=module,
            timestamp=timestamp,
        ))
        self.send_requests(module, requests)
        print(f"Sent requests to '{module}' module for '{resource.resource}'")

    def _process(
        self, identifier: str, module: str
    ):
        key = module + " - " + identifier
        if key in self.cache:
            return ([], [])
        self.cache[key] = True
        resource = Resource(identifier, [module])
        for module in resource.modules:
            match module:
                case "http":
                    return self.send_request_for_resource(resource, module)
                case "dns":
                    return self.send_request_for_resource(resource, module)
                case "github":
                    return self.send_request_for_resource(resource, module)
                case other:
                    sys.exit(f"Target '{module}' not supported!")
        return

    def process_discovery(self, module: str, discovery: Discovery):
        if discovery.module != module:
            self.discovery_backlog.append(discovery)
            return
        print("Discovery: " + discovery.resource)
        self.database.upsert_resource(
            Resource.from_discovery(discovery), discovery.source
        )

    def initiate_requests(self, entry: Resource):
        resource = entry.resource
        for module in entry.modules:
            self._process(resource, module)

    def update_config(self, target: ConfigTarget):
        resource = Resource.from_target(target)
        self.database.upsert_resource(resource, "config.json")

    def setup_requests(self):
        for resource in self.database.get_resources():
            self.initiate_requests(resource)

    def process_response(self, module, response: ModuleResponse):
        if response["operation"] == "observation":
            observation = response_to_observation(response)
            self.database.upsert_observations(observation)
            return
        discovery = response_to_discovery(response)
        self.process_discovery(module, discovery)

    def process_responses(self):
        # (Non-blocking) Opportunistically process responses which are ready:
        for name,module in self.modules.items():
            callback = lambda response: self.process_response(name, response)
            module.process_responses(callback)
        # (Blocking) Wait for everything to finish:
        for name,module in self.modules.items():
            callback = lambda response: self.process_response(name, response)
            module.process_all_responses(callback)
        self.process_discovery_backlog()

    def update(self):
        clear_get_cache()

        # Read config
        config = JsonFile("config/config.json")

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
            target = ConfigTarget(target["resource"], target["module"])
            self.update_config(target)

        self.setup_requests()
        self.process_responses()

        # Commit snapshot
        metadata["last_update"] = {"time": time, "name": snapshot_name, "seq": seq}
        metadata.save()
        metadata.save(os.path.join(self.snapshot, "metadata.json"))


def forever():
    while True:
        updater = Updater()
        updater.update()
        sleep(10)


def once():
    updater = Updater()
    updater.update()
