import copy

import requests


class HTTPGet:
    """Abstraction / encapsulation of requests.get()

    Expose only the properties we actually need.
    """

    def __init__(self, url):
        self._r = requests.get(url, allow_redirects=False)
        self._url = url

    @property
    def url(self):
        return self._url

    @property
    def status_code(self):
        return self._r.status_code

    @property
    def redirect_location(self):
        return self._r.headers.get("Location")


def strip_prefix(inp, options, n):
    if n == 0:
        return inp
    for prefix in options:
        if inp.startswith(prefix):
            return strip_prefix(inp[len(prefix) :], options, n - 1)
    return inp


def simplify_url(url):
    if url.endswith("/"):
        return simplify_url(url[0:-1])
    return strip_prefix(url, ("http://", "https://"), 1)


def is_root_url(url):
    return "/" not in url


def is_https_url(url):
    return url.startswith("https://")


def https_to_http(url):
    assert url.startswith("https://")
    return "http://" + url[len("https://") :]


def module_http(entry):
    def get_status_code_and_location(url):
        r = requests.get(url, allow_redirects=False)
        return r.status_code, r.headers.get("Location")

    results = []
    discoveries = []

    while entry["identifier"].endswith("/"):
        entry["identifier"] = entry["identifier"][0:-1]
    r = HTTPGet(entry["identifier"])

    entry["type"] = "status"
    entry["value"] = r.status_code
    results.append(copy.deepcopy(entry))

    if r.redirect_location:
        print(f"Website: {r.url} -> {r.redirect_location} ({r.status_code})")
        entry["type"] = "redirect_location"
        entry["value"] = r.redirect_location
        results.append(copy.deepcopy(entry))
        discoveries.append(
            {
                "module": "http",
                "identifier": redirect_location,
            }
        )
    else:
        print(f"Website: {r.url} -> {r.status_code}")

    if is_https_url(r.url) and is_root_url(r.url):
        http_entry = {}
        http_entry["module"] = "http"
        http_entry["identifier"] = https_to_http(r.url)
        discoveries.append(http_entry)

    return (results, discoveries)
