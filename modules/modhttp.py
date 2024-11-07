import sys
import json
import fileinput
import datetime
import requests
from functools import cache
from urllib.parse import urlparse


def now() -> int:
    return int(datetime.datetime.now().timestamp())


class Response:
    def __init__(self, r):
        self._r = r
        self.url = r.url
        self.status_code = r.status_code
        self.redirect_location = r.headers.get("Location", None)
        self.body = r.text
        self.timestamp = now()
        self.notable_headers = {}

        for header in [
            "Location",
            "Content-Security-Policy",
            "Permissions-Policy",
            "Referrer-Policy",
            "Server",
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-Xss-Protection",
        ]:
            key = header.lower().replace("-", "_")
            value = r.headers.get(header, "")
            self.notable_headers[key] = value


@cache
def http_get(url: str):
    r = Response(requests.get(url, allow_redirects=False))
    return r


def is_root_url(url: str):
    res = urlparse(url)
    return res.path == "/" or res.path == ""


@cache
def normalize_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        return url
    if not is_root_url(url):
        return url
    while url.endswith("/"):
        url = url[0:-1]
    return url + "/"


def url_to_hostname(url: str) -> str:
    if url.startswith("https://"):
        url = url[len("https://") :]
    elif url.startswith("http://"):
        url = url[len("http://") :]
    index = url.rfind("/")
    if index >= 0:
        return url[0:index]
    return url


def handle_request(request: dict) -> list[dict]:
    assert type(request.get("operation", None)) is str
    assert type(request.get("resource", None)) is str
    assert type(request.get("module", None)) is str
    assert request["module"] == "http"

    url = normalize_url(request["resource"])
    r = http_get(url)

    if request["operation"] == "discovery":
        discoveries = []
        discoveries.append(
            {
                "operation": "discovery",
                "resource": url,
                "module": "http",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        )
        if url.startswith("https://"):
            discoveries.append(
                {
                    "operation": "discovery",
                    "resource": url[0:4] + url[5:],
                    "module": "http",
                    "source": "http",
                    "timestamp": request["timestamp"],
                }
            )
        discoveries.append(
            {
                "operation": "discovery",
                "resource": url_to_hostname(url),
                "module": "dns",
                "source": "http",
                "timestamp": request["timestamp"],
            }
        )
        return discoveries

    assert request["operation"] == "observation"

    observations = []
    observations.append(
        {
            "operation": request["operation"],
            "resource": url,
            "module": "http",
            "attribute": "status_code",
            "value": r.status_code,
            "timestamp": r.timestamp,
        }
    )
    for key, value in r.notable_headers.items():
        observations.append(
            {
                "operation": request["operation"],
                "resource": url,
                "module": "http",
                "attribute": key,
                "value": value,
                "timestamp": r.timestamp,
            }
        )

    return observations


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
            "resource": "https://cfengine.com",
            "source": "config.json",
            "module": "http",
            "timestamp": 1730241747,
        },
        {
            "operation": "observation",
            "resource": "https://cfengine.com",
            "module": "http",
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
