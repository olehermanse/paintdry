from datetime import timedelta
from time import sleep
from functools import cache

import requests
import requests_cache

from modlib import ModBase, now, normalize_url, url_to_hostname, is_root_url


def good_paths():
    return ("security.txt", ".well-known/security.txt")


def bad_paths():
    return (
        "Dockerfile",
        "package.json",
        "package-lock.json",
        "README.md",
        "Makefile",
        "authorized_keys",
        "known_hosts",
        "go.mod",
    )


def well_known_paths():
    return (*good_paths(), *bad_paths())


def ends_with_one_of(url, paths):
    for path in paths:
        if url.endswith("/" + path):
            return True
    return False


def is_known_path(url):
    return ends_with_one_of(url, well_known_paths())


def severity_from_status_code(url, status_code):
    if status_code == 500:
        return "critical"
    if url.endswith("/security.txt"):
        if status_code in (200, 301, 302):
            return "none"
        if status_code == 404:
            return "medium"
        return "high"
    if url.startswith("http://"):
        if status_code == 301:
            return "none"
        if status_code in (404, 403, 302) and ends_with_one_of(url, bad_paths()):
            return "none"
        return "high"
    if status_code == 200:
        if ends_with_one_of(url, bad_paths()):
            return "medium"
        return "none"
    if status_code == 404:
        if ends_with_one_of(url, bad_paths()):
            return "none"
        return "low"
    if status_code == 301:
        return "low"
    return "low"


class Response:
    """Wrapper around a response from requests, exposing only what we need"""

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
    while True:
        try:
            r = requests.get(url, allow_redirects=False)
            if r.from_cache:
                print("CACHE HIT: " + url)
            if not r.from_cache:
                # Real HTTP request made, throttle to be nice,
                # reducing network load and avoiding rate limits:
                sleep(0.2)
                if r.status_code not in (200, 301, 404):
                    # If we encounter other unexpected codes,
                    # like 500 for example, slow down further:
                    sleep(0.8)
            return Response(r)
        except:
            print(f"GET failed unexpectedly: {url}")
            sleep(2)
            continue


class ModHTTP(ModBase):
    def example_requests(self):
        return [
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

    def discovery(self, request: dict) -> list[dict]:
        url = normalize_url(request["resource"])

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
        if url.startswith("https://") and is_root_url(url):
            for path in well_known_paths():
                discoveries.append(
                    {
                        "operation": "discovery",
                        "resource": url + path,
                        "module": "http",
                        "source": "http",
                        "timestamp": request["timestamp"],
                    }
                )
        hostname = url_to_hostname(url)
        root_url = normalize_url("https://" + hostname)
        discoveries.append(
            {
                "operation": "discovery",
                "resource": hostname,
                "module": "dns",
                "source": "http",
                "timestamp": request["timestamp"],
            }
        )
        discoveries.append(
            {
                "operation": "discovery",
                "resource": root_url,
                "module": "tls",
                "source": "http",
                "timestamp": request["timestamp"],
            }
        )
        return discoveries

    def observation(self, request: dict) -> list[dict]:
        url = normalize_url(request["resource"])
        observations = []

        r = http_get(url)

        status_code = r.status_code
        severity = severity_from_status_code(url, status_code)
        print(f"Got severity {severity} for {status_code} on {url}")

        observations.append(
            {
                "operation": request["operation"],
                "resource": url,
                "module": "http",
                "attribute": "status_code",
                "value": status_code,
                "timestamp": r.timestamp,
                "severity": severity,
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
                    "severity": "none",
                }
            )
        return observations


def main():
    mod = ModHTTP()
    mod.main()


if __name__ == "__main__":
    main()
