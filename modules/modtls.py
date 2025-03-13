import ssl
from functools import cache
from datetime import datetime, timezone

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import requests

from modlib import ModBase, now, normalize_url, url_to_hostname


@cache
def cert_checks(url: str):
    url = normalize_url(url)
    try:
        requests.get(url)
    except:
        return ("critical", "invalid")
    url = url[len("https://") : -1]
    print(f"Looking up TLS cert for {url}")
    r = ssl.get_server_certificate((url, 443)).encode("utf-8")
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
                "source": request["source"],
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


def main():
    mod = ModTLS()
    mod.main()


if __name__ == "__main__":
    main()
