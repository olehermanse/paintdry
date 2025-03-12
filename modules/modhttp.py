import requests
from time import sleep
from functools import cache
from modlib import ModBase, now, normalize_url, url_to_hostname


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
    sleep(1)
    r = Response(requests.get(url, allow_redirects=False))
    if r.status_code != 200:
        sleep(3)
    return r


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
        r = http_get(url)

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

    def observation(self, request: dict) -> list[dict]:
        url = normalize_url(request["resource"])
        r = http_get(url)
        status_code = r.status_code
        severity = ""
        if status_code == 200:
            severity = "none" if url.startswith("https://") else "high"
        elif status_code == 301:
            severity = "none" if url.startswith("http://") else "low"
        elif status_code == 500:
            severity = "critical"
        elif status_code == 404:
            severity = "medium"
        else:
            status_code = "low"
        observations = []
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
