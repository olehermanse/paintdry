import ssl
from functools import cache
from datetime import datetime, timezone, timedelta
from time import sleep

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import requests
import requests_cache

from modlib import ModBase, now, normalize_url, url_to_hostname, respond_with_severity


@cache
def cert_checks(url: str):
    url = normalize_url(url)
    try:
        r = requests.get(url, allow_redirects=False)
        if r.from_cache:
            print("CACHE HIT: " + url)
        if not r.from_cache:
            sleep(0.2)
    except:
        print(f"Exception encountered when looking up cert for {url}")
        return ("critical", "invalid")
    url = url[len("https://") : -1]
    print(f"Looking up TLS cert for {url}")
    r = ssl.get_server_certificate((url, 443)).encode("utf-8")
    sleep(1)
    cert = x509.load_pem_x509_certificate(r, default_backend())
    expires = datetime.fromisoformat(str(cert.not_valid_after_utc))
    delta = expires - datetime.now(timezone.utc)
    if delta.days > 30:
        return ("none", "valid (>30 days)")
    if delta.days >= 21:
        return ("low", "valid (21-30 days)")
    if delta.days >= 14:
        return ("low", "valid (14-20 days)")
    if delta.days >= 7:
        return ("medium", "valid (7-14 days)")
    if delta.days >= 1:
        return ("high", "valid (1-7 days)")
    return ("critical", "valid (<1 day)")


class ModTLS(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "https://cfengine.com",
                "source": "config.json",
                "module": "tls",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "https://cfengine.com",
                "module": "tls",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> list[dict]:
        url = normalize_url(request["resource"])

        if not url.startswith("https://"):
            return []

        discoveries = []
        discoveries.append(
            {
                "operation": "discovery",
                "resource": url,
                "module": "tls",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        )
        discoveries.append(
            {
                "operation": "discovery",
                "resource": url_to_hostname(url),
                "module": "dns",
                "source": "tls",
                "timestamp": request["timestamp"],
            }
        )
        return discoveries

    def observation(self, request: dict) -> list[dict]:
        url = normalize_url(request["resource"])

        if not url.startswith("https://"):
            return []

        observations = []
        severity, validity = cert_checks(url)
        observations.append(
            {
                "operation": request["operation"],
                "resource": url,
                "module": "tls",
                "attribute": "certificate",
                "value": validity,
                "timestamp": now(),
                "severity": severity,
            }
        )
        return observations

    def change(self, request):
        if request["new_value"] == "invalid":
            return respond_with_severity(request, "critical")
        return respond_with_severity(request, "notice")


def main():
    mod = ModTLS()
    mod.main()


if __name__ == "__main__":
    main()
