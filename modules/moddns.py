import sys
import json
import fileinput
import socket
import datetime
import time
from functools import cache


def now() -> int:
    return int(datetime.datetime.now().timestamp())


@cache
def dns_lookup(hostname: str) -> tuple[int, list[str]]:
    time.sleep(1)
    results = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    return (now(), sorted([x[4][0] for x in results]))


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


def handle_request(request: dict) -> list[dict]:
    assert type(request.get("operation", None)) is str
    assert type(request.get("resource", None)) is str
    assert type(request.get("module", None)) is str
    assert request["module"] == "dns"

    resource = normalize_hostname(request["resource"])
    timestamp, ips = dns_lookup(resource)

    if request["operation"] == "discovery":
        # DNS module currently does not discover anything extra
        # Just confirm the requested resource:
        return [
            {
                "operation": "discovery",
                "resource": normalize_hostname(resource),
                "module": "dns",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        ]

    assert request["operation"] == "observation"
    response = {
        "operation": request["operation"],
        "resource": normalize_hostname(resource),
        "module": "dns",
        "attribute": "ip",
        "value": ", ".join(ips),
        "timestamp": timestamp,
    }
    return [response]


def handle_line(line):
    request = json.loads(line)
    assert type(request) is dict
    results = handle_request(request)
    for result in results:
        print(json.dumps(result))
    print()


def main_loop():
    history = set()
    for line in fileinput.input(encoding="utf-8"):
        line = line.strip()  # Normalize / remove trailing newline

        # Skip empty lines:
        if not line:
            print()
            continue

        assert line[0] == "{" and line[-1] == "}"
        # Skip duplicate requests
        # Just a precaution, shouldn't be necessary
        if line in history:
            continue
        history.add(line)

        # Actually handle request and output results:
        handle_line(line)


def run_example():
    requests = [
        {
            "operation": "discovery",
            "resource": "www.cfengine.com",
            "module": "dns",
            "source": "config.json",
            "timestamp": 1730241747,
        },
        {
            "operation": "observation",
            "resource": "www.cfengine.com",
            "module": "dns",
            "timestamp": 1730241747,
        },
    ]
    for request in requests:
        line = json.dumps(request)
        print("Example request:")
        print(line)
        print()
        print("Response(s):")
        handle_line(line)
        print()
    return


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "example":
        run_example()
        return
    main_loop()


if __name__ == "__main__":
    main()
