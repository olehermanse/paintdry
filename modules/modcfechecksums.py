from functools import cache
from collections.abc import Iterable

import requests

from modlib import ModBase, now, respond_with_severity, TAG_REGEX

RELEASES_URL = "https://cfengine.com/release-data/enterprise/releases.json"

@cache
def download_and_extract(url):
    assert url != RELEASES_URL
    data = {}
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Failed to download {url}")
        return {}
    response = r.json()
    for role in response["artifacts"]:
        for artifact in response["artifacts"][role]:
            checksum = artifact["SHA256"]
            url = artifact["URL"]
            data[url] = checksum
    return data

@cache
def get_all_checksums(url):
    assert url == RELEASES_URL
    r = requests.get(url)
    data = r.json()
    all = {}
    for release in data["releases"]:
        if "alpha" in release:
            continue
        if "lts_branch" not in release:
            continue
        if "URL" not in release:
            continue
        version = release["version"]
        if not TAG_REGEX.fullmatch(version):
            continue
        r = download_and_extract(release["URL"])
        all.update(r)
    return all

@cache
def get_checksum(url):
    all = get_all_checksums(RELEASES_URL)
    if not url in all:
        return None
    return all[url]

class ModCFEChecksums(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "https://cfengine.com/release-data/enterprise/releases.json",
                "module": "cfechecksums",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "https://cfengine.com/release-data/enterprise/releases.json",
                "module": "cfechecksums",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> Iterable[dict]:
        url = request["resource"]
        if not url.endswith("/releases.json"):
            return
        yield {
            "operation": "discovery",
            "resource": url,
            "module": "cfechecksums",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }

    def observation(self, request: dict) -> Iterable[dict]:
        url = request["resource"]
        if not url.endswith("/releases.json"):
            return
        assert url == RELEASES_URL
        all = get_all_checksums(url)
        if not all:
            return
        for artifact, checksum in all.items():
            yield {
                "operation": "observation",
                "resource": url,
                "module": "cfechecksums",
                "attribute": artifact,
                "value": checksum,
                "timestamp": now(),
                "severity": "none",
            }

    def change(self, request) -> Iterable[dict]:
        assert request["new_value"] != request["old_value"]
        yield from respond_with_severity(request, "high")


def main():
    module = ModCFEChecksums()
    module.main()


if __name__ == "__main__":
    main()
