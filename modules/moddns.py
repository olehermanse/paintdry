import socket
import time
from functools import cache
from collections.abc import Iterable
from modlib import ModBase, now, normalize_hostname, respond_with_severity


@cache
def dns_lookup(hostname: str) -> tuple[int, list[str]]:
    time.sleep(1)
    try:
        results = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        return (now(), sorted([str(x[4][0]) for x in results]))
    except:
        return (now(), [])


class ModDNS(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "example.com",
                "module": "dns",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "example.com",
                "module": "dns",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> Iterable[dict]:
        resource = normalize_hostname(request["resource"])
        # DNS module currently does not discover anything extra
        # Just confirm the requested resource:
        yield {
            "operation": "discovery",
            "resource": normalize_hostname(resource),
            "module": "dns",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }

    def observation(self, request: dict) -> Iterable[dict]:
        assert request["module"] == "dns"

        resource = normalize_hostname(request["resource"])
        timestamp, ips = dns_lookup(resource)
        if not ips:
            return
        yield {
            "operation": "observation",
            "resource": normalize_hostname(resource),
            "module": "dns",
            "attribute": "ip",
            "value": ips,
            "timestamp": timestamp,
            "severity": "none" if len(ips) > 0 else "high",
        }

    def change(self, request) -> Iterable[dict]:
        if request["new_value"] == "":
            yield from respond_with_severity(request, "high")
            return
        yield from respond_with_severity(request, "notice")


def main():
    module = ModDNS()
    module.main()


if __name__ == "__main__":
    main()
