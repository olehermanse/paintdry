import os
from pathlib import Path
import sys
import json
import fileinput
import datetime
from urllib.parse import urlparse


def now() -> int:
    return int(datetime.datetime.now().timestamp())


def is_root_url(url: str):
    res = urlparse(url)
    return res.path == "/" or res.path == ""


def strip_prefix(prefix, string) -> str:
    if string.startswith(prefix):
        return string[len(prefix) :]
    return string


def url_to_hostname(url: str) -> str:
    if url.startswith("https://"):
        url = url[len("https://") :]
    elif url.startswith("http://"):
        url = url[len("http://") :]
    index = url.rfind("/")
    if index >= 0:
        return url[0:index]
    return url


def normalize_hostname(hostname: str) -> str:
    hostname = url_to_hostname(hostname)
    if hostname.startswith("www."):
        return hostname[4:]
    return hostname


def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return "https://" + url
    if not is_root_url(url):
        return url
    while url.endswith("/"):
        url = url[0:-1]
    return url + "/"


class ModBase:
    def example_requests(self):
        return []

    def discovery(self, request: dict) -> list[dict]:
        return []

    def observation(self, request: dict) -> list[dict]:
        return []

    def handle_request(self, request: dict) -> list[dict]:
        assert type(request.get("operation", None)) is str
        assert type(request.get("resource", None)) is str
        assert type(request.get("module", None)) is str
        if request["operation"] == "discovery":
            return self.discovery(request)
        if request["operation"] == "observation":
            return self.observation(request)
        return []

    def handle_line(self, line):
        request = json.loads(line)
        assert type(request) is dict
        results = self.handle_request(request)
        for result in results:
            print(json.dumps(result))
        print()

    def handle_stdin_stdout(self):
        history = set()
        for line in fileinput.input(encoding="utf-8"):
            line = line.strip()  # Normalize / remove trailing newline

            # Skip empty lines:
            if not line:
                continue

            assert line[0] == "{" and line[-1] == "}"
            # Skip duplicate requests
            # Just a precaution, shouldn't be necessary
            if line in history:
                continue
            history.add(line)

            # Actually handle request and output results:
            self.handle_line(line)

    def handle_single_file(self, input_dir, name, output_dir):
        input_file = Path(input_dir, name)
        output_file = Path(output_dir, name)
        with open(input_dir + "/" + name, "r") as f:
            data = json.loads(f.read())
        results = []
        if type(data) is dict:
            results = self.handle_request(data)
        else:
            for element in data:
                results.extend(self.handle_request(element))
        assert type(results) is list
        with open(output_dir + "/" + name, "w") as f:
            f.write(json.dumps(results))
        input_file.unlink()

    def handle_files(self, input_dir, output_dir):
        assert os.path.isdir(input_dir)
        assert os.path.isdir(output_dir)
        with os.scandir(input_dir) as it:
            for entry in it:
                if not entry.is_file() or not entry.name.endswith(".json"):
                    continue
                self.handle_single_file(input_dir, entry.name, output_dir)

    def run_example(self):
        requests = self.example_requests()
        for request in requests:
            line = json.dumps(request)
            print("Example request:")
            print(line)
            print()
            print("Response(s):")
            self.handle_line(line)
            print()
        return

    def main(self):
        if len(sys.argv) == 2 and sys.argv[1] == "example":
            self.run_example()
            return
        if len(sys.argv) == 3:
            self.handle_files(sys.argv[1], sys.argv[2])
            return
        self.handle_stdin_stdout()
