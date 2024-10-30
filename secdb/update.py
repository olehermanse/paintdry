import os
import sys
import json
import datetime
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


class Updater:
    def __init__(self):
        self.database = Database()
        self.cache = {}
        self.externals = {}
        self.discovery_backlog = []

    def send_request(self, module: str, request: ModuleRequest):
        process = self.get_process(module)
        a = json.dumps(request)
        process.stdin.write(a + "\n")
        process.stdin.flush()

    def get_process(self, module: str):
        config = JsonFile("config.json")
        if not module in self.externals:
            print(f"Starting '{module}' module")
            command = config["modules"][module]["command"]
            self.externals[module] = Popen(
                command,
                shell=True,
                text=True,
                encoding="utf-8",
                stdin=PIPE,
                stdout=PIPE,
                stderr=STDOUT,
            )
        return self.externals[module]

    def receive_responses(self, module: str) -> list[ModuleResponse]:
        process = self.get_process(module)
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
        for discovery in self.discovery_backlog:
            request = ModuleRequest(
                operation="discovery",
                resource=discovery["resource"],
                module=discovery["module"],
                source=discovery["source"],
                timestamp=now(),
            )
            self.send_request(discovery["module"], request)
        for discovery in self.discovery_backlog:
            responses = self.receive_responses(discovery["module"])
            for response in responses:
                if response["module"] == discovery["module"]:
                    observation = response_to_observation(response)
                    self.database.upsert_observations(observation)
        self.discovery_backlog = []

    def process_discoveries(self, module: str, discoveries: list[Discovery]):
        for discovery in discoveries:
            if discovery.module != module:
                self.discovery_backlog.append(discovery)
                continue
            source = discovery.source
            resource = Resource.from_discovery(discovery)
            self.database.upsert_resource(resource, source)

    def handle_external_module(self, resource: Resource, module: str):
        print(f"Sending requests to '{module}' module for '{resource.resource}'")
        source = resource["source"]
        if not source:
            source = ""  # TODO FIXME
        request = ModuleRequest(
            operation="discovery",
            resource=resource.resource,
            module=module,
            source=source,
            timestamp=now(),
        )
        self.send_request(module, request)
        request["operation"] = "observation"
        self.send_request(module, request)
        print(f"Sent requests to '{module}' module for '{resource.resource}'")

        discoveries = [response_to_discovery(x) for x in self.receive_responses(module)]
        print(f"Received discoveries from '{module}' module for '{resource.resource}'")

        self.process_discoveries(module, discoveries)

        observations = [
            response_to_observation(x) for x in self.receive_responses(module)
        ]

        print(f"Received discoveries from '{module}' module for '{resource.resource}'")

        return (observations, discoveries)

    def _process(
        self, identifier: str, module: str
    ) -> tuple[list[Observation], list[Discovery]]:
        key = module + " - " + identifier
        if key in self.cache:
            return ([], [])
        self.cache[key] = True
        resource = Resource(identifier, [module])
        for module in resource.modules:
            match module:
                case "http":
                    return self.handle_external_module(resource, module)
                case "dns":
                    return self.handle_external_module(resource, module)
                case other:
                    sys.exit(f"Target '{module}' not supported!")
        return ([], [])

    def process_discovery(self, discovery: Discovery):
        print("Discovery: " + discovery.resource)
        self.database.upsert_resource(
            Resource.from_discovery(discovery), discovery.source
        )

    def process_resource(self, entry: Resource):
        resource = entry.resource
        for module in entry.modules:
            results, discoveries = self._process(resource, module)
            for result in results:
                self.database.upsert_observations(result)
            for e in discoveries:
                self.process_discovery(e)

    def update_config(self, target: ConfigTarget):
        self.database.upsert_config(target)
        resource = Resource.from_target(target)
        self.database.upsert_resource(resource, "config.json")

    def update(self):
        clear_get_cache()

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
            target = ConfigTarget(target["resource"], target["module"])
            self.update_config(target)

        for resource in self.database.get_resources():
            self.process_resource(resource)

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
