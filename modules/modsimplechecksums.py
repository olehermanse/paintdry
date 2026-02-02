from functools import cache

import requests

from modlib import ModBase, now, respond_with_severity, normalize_url


@cache
def download_and_parse_checksums(url):
    """Download a checksums.txt file and parse it into a dict of filename -> checksum."""
    data = {}
    r = requests.get(url)
    if r.status_code != 200:
        print(f"Failed to download {url}")
        return {}
    for line in r.text.splitlines():
        line = line.strip()
        if not line:
            continue
        # sha256sum format: <checksum>  <filename> (two spaces between)
        # Also handle single space for compatibility
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        checksum, filename = parts
        # Remove leading ./ or * from filename if present
        filename = filename.lstrip("*")
        if filename.startswith("./"):
            filename = filename[2:]
        data[filename] = checksum
    return data


class ModSimpleChecksums(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "https://example.com/checksums.txt",
                "module": "simplechecksums",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "https://example.com/checksums.txt",
                "module": "simplechecksums",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> list[dict]:
        url = normalize_url(request["resource"])
        return [{
            "operation": "discovery",
            "resource": url,
            "module": "simplechecksums",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }]

    def observation(self, request: dict) -> list[dict]:
        url = request["resource"]
        checksums = download_and_parse_checksums(url)
        if not checksums:
            return []
        observations = []
        for filename, checksum in checksums.items():
            observations.append({
                "operation": "observation",
                "resource": url,
                "module": "simplechecksums",
                "attribute": filename,
                "value": checksum,
                "timestamp": now(),
                "severity": "none",
            })
        return observations

    def change(self, request):
        assert request["new_value"] != request["old_value"]
        return respond_with_severity(request, "high")


def main():
    module = ModSimpleChecksums()
    module.main()


if __name__ == "__main__":
    main()
