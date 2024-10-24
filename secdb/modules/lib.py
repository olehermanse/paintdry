from ast import Attribute
import datetime
from typing import Any
import requests

from secdb.utils import normalize_url


class ConfigTarget:
    """User specified targets in config.json / config table"""

    def __init__(self, resource, module):
        self.resource = normalize_url(resource)
        self.module = module


class Discovery:
    def __init__(self, resource, modules, source):
        self.resource = normalize_url(resource)
        self.modules = modules
        self.source = source
        self.timestamp = datetime.datetime.now()


class Observation:
    def __init__(self, resource: str, module: str, attribute: str, value: str):
        self.resource = normalize_url(resource)
        self.module = module
        self.attribute = attribute
        self.value = str(value)
        self.timestamp = datetime.datetime.now()


class Resource(dict):
    def __init__(
        self,
        resource: str,
        modules: list[str],
        id=None,
        source=None,
        first_seen=None,
        last_seen=None,
    ):
        dict.__init__(
            self,
            resource=resource,
            modules=modules,
            id=id,
            source=source,
            first_seen=first_seen,
            last_seen=last_seen,
        )

    @property
    def resource(self):
        return self["resource"]

    @property
    def modules(self):
        return self["modules"]

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name not in self:
            raise AttributeError
        return super().__setattr__(name, value)

    def __getattribute__(self, name: str, /) -> Any:
        return super().__getattribute__(name)

    @staticmethod
    def from_target(target: ConfigTarget):
        return Resource(target.resource, [target.module])

    @staticmethod
    def from_discovery(discovery: Discovery):
        return Resource(discovery.resource, discovery.modules)


class Response:
    def __init__(self, r):
        self._r = r
        self.url = r.url
        self.status_code = r.status_code
        self.redirect_location = r.headers.get("Location", None)
        self.body = r.text
        self.timestamp = datetime.datetime.now()


_get_cache: dict[str, Response] = {}


def cached_http_get(url: str):
    print("GET " + url)
    global _get_cache
    if url in _get_cache:
        return _get_cache[url]
    r = Response(requests.get(url, allow_redirects=False))
    _get_cache[url] = r
    return r


def clear_get_cache():
    global _get_cache
    _get_cache = {}
