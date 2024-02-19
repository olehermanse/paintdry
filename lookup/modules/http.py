import copy

import requests


def is_root_url(url):
    return url.endswith((".io", ".com", ".tech", ".io/", ".com/", ".tech/"))


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
    url = entry["identifier"]
    code, redirect_location = get_status_code_and_location(url)

    entry["type"] = "status"
    entry["value"] = code
    results.append(copy.deepcopy(entry))

    if redirect_location:
        print(f"Website: {url} -> {redirect_location} ({code})")
        entry["type"] = "redirect_location"
        entry["value"] = redirect_location
        results.append(copy.deepcopy(entry))
        discoveries.append(
            {
                "module": "http",
                "identifier": redirect_location,
            }
        )
    else:
        print(f"Website: {url} -> {code}")

    if is_https_url(url) and is_root_url(url):
        http_entry = {}
        http_entry["module"] = "http"
        http_entry["identifier"] = https_to_http(url)
        discoveries.append(http_entry)

    return (results, discoveries)
