import socket
import time
from functools import cache
from modlib import ModBase, now, normalize_hostname, respond_with_severity


@cache
def dns_lookup(hostname: str) -> tuple[int, list[str]]:
    time.sleep(1)
    try:
        results = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        return (now(), sorted([x[4][0] for x in results]))
    except:
        return (now(), [])


class ModDNS(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "cfengine.com",
                "module": "dns",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "cfengine.com",
                "module": "dns",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> list[dict]:
        resource = normalize_hostname(request["resource"])
        timestamp, ips = dns_lookup(resource)
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

    def observation(self, request: dict) -> list[dict]:
        assert request["module"] == "dns"

        resource = normalize_hostname(request["resource"])
        timestamp, ips = dns_lookup(resource)
        if not ips:
            return []
        return [
            {
                "operation": request["operation"],
                "resource": normalize_hostname(resource),
                "module": "dns",
                "attribute": "ip",
                "value": ", ".join(ips),
                "timestamp": timestamp,
                "severity": "none" if len(ips) > 0 else "high",
            }
        ]

    def change(self, request):
        if request["new_value"] == "":
            return respond_with_severity(request, "high")
        return respond_with_severity(request, "notice")


def main():
    module = ModDNS()
    module.main()


if __name__ == "__main__":
    main()
