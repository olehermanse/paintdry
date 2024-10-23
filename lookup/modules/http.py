from lookup.modules.lib import cached_http_get, Observation, Resource, Discovery
from lookup.utils import is_root_url, is_https_url, https_to_http, normalize_url

class HTTPModule:
    @staticmethod
    def process(resource: Resource) -> tuple[list[Observation],list[Discovery]]:
         return (HTTPModule.observe(resource), HTTPModule.discover(resource))

    @staticmethod
    def discover(resource: Resource) -> list[Discovery]:
        discoveries = []
        url = normalize_url(resource.resource)
        while url.endswith("/"):
            url = url[0:-1]
        response = cached_http_get(url)

        # Discover a redirect:
        location = response.redirect_location
        if location:
            discoveries.append(Discovery(location, ["http"], "http"))

        # Discover the http version of an HTTPS URL:
        if is_https_url(url) and is_root_url(url):
            http_url = normalize_url(https_to_http(url))
            discoveries.append(Discovery(http_url, ["http"], "http"))

        return discoveries

    @staticmethod
    def observe(resource: Resource) -> list[Observation]:
        results = []
        url = normalize_url(resource.resource)
        while url.endswith("/"):
            url = url[0:-1]
        response = cached_http_get(url)
        results.append(Observation(url, "http", "status_code", response.status_code))

        location = response.redirect_location
        if location:
            print(f"Website: {url} -> {location} ({response.status_code})")
            results.append(Observation(url, "http", "redirect_location", location))
        else:
            print(f"Website: {url} -> {response.status_code}")

        return results
