import json
import datetime
from typing import Any

import requests


class ModuleRequest(dict):
    def __init__(
        self,
        operation: str,
        resource: str,
        module: str,
        timestamp: int,
        source: str | None = None,
    ):
        dict.__init__(
            self,
            operation=operation,
            resource=resource,
            source=source,
            module=module,
            timestamp=timestamp,
        )
        if source is None:
            del self["source"]
        self.validate()

    def validate(self):
        for key in self:
            if key == "timestamp":
                assert type(self[key]) is int
            else:
                if not type(self[key]) is str:
                    print(f"Error: key '{key}' is not str; " + json.dumps(self))
                assert type(self[key]) is str
        assert self["operation"] in ["discovery", "observation"]
        if self["operation"] == "discovery":
            print(json.dumps(self))
            assert "source" in self
            assert type(self["source"]) is str
            return

        # observation:
        assert "source" not in self

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name not in self:
            raise AttributeError
        return super().__setattr__(name, value)

    @staticmethod
    def example():
        data = {
            "operation": "discovery",
            "resource": "https://cfengine.com",
            "source": "config.json",
            "module": "http",
            "timestamp": 1730241747,
        }
        return ModuleRequest(**data)

    @staticmethod
    def convert(arg: dict | str):
        if type(arg) is str:
            return ModuleRequest(**json.loads(arg))
        assert type(arg) == dict
        return ModuleRequest(**arg)


class ModuleResponse(dict):
    def __init__(
        self,
        operation: str,
        resource: str,
        module: str,
        timestamp: int,
        source: str | None = None,
        attribute: str | None = None,
        value: str | int | None = None,
    ):
        dict.__init__(
            self,
            operation=operation,
            resource=resource,
            module=module,
            timestamp=timestamp,
            source=source,
            attribute=attribute,
            value=value,
        )
        for key in ["value", "source", "attribute"]:
            if self[key] is None:
                del self[key]
        self.validate()

    def validate(self):
        for key in self:
            if key == "value":
                assert type(self[key]) in (str, int)
            elif key == "timestamp":
                assert type(self[key]) is int
            else:
                assert type(self[key]) is str, f"Wrong type {key}; {json.dumps(self)}"
        assert self["operation"] in ["discovery", "observation"]
        if self["operation"] == "discovery":
            assert "source" in self and type(self["source"]) is str
            assert "attribute" not in self
            assert "value" not in self
            return

        # observation:
        assert "source" not in self
        assert "attribute" in self
        assert "value" in self

    @staticmethod
    def example():
        data = {
            "operation": "discovery",
            "resource": "cfengine.com",
            "module": "dns",
            "source": "http",
            "timestamp": 1730241747,
        }
        return ModuleResponse(**data)

    @staticmethod
    def convert(arg: dict | str):
        if type(arg) is str:
            return ModuleResponse(**json.loads(arg))
        assert type(arg) == dict
        return ModuleResponse(**arg)


class ConfigTarget(dict):
    """User specified targets in config.json / config table"""

    def __init__(
        self, resource: str, module: str, id=None, first_seen=None, last_seen=None
    ):
        dict.__init__(
            self,
            resource=resource,
            module=module,
            id=id,
            first_seen=first_seen,
            last_seen=last_seen,
        )

    @property
    def resource(self):
        return self["resource"]

    @property
    def module(self):
        return self["module"]


class Discovery:
    def __init__(self, resource, module, source, timestamp=None):
        self.resource = resource
        self.module = module
        self.source = source
        if not timestamp:
            timestamp = datetime.datetime.now()
        self.timestamp = None


class Observation(dict):
    def __init__(
        self,
        resource: str,
        module: str,
        attribute: str,
        value: str,
        id=None,
        first_seen=None,
        last_changed=None,
        last_seen=None,
        timestamp=None,
        severity=str,
    ):
        if type(timestamp) is int:
            timestamp = datetime.datetime.fromtimestamp(timestamp)
        if not timestamp:
            timestamp = datetime.datetime.now()
        dict.__init__(
            self,
            resource=resource,
            module=module,
            attribute=attribute,
            value=str(value),
            id=id,
            first_seen=first_seen,
            last_changed=last_changed,
            last_seen=last_seen,
            timestamp=timestamp,
            severity=severity,
        )

    @property
    def resource(self):
        return self["resource"]

    @property
    def module(self):
        return self["module"]

    @property
    def attribute(self):
        return self["attribute"]

    @property
    def value(self):
        return self["value"]

    @property
    def timestamp(self):
        return self["timestamp"]

    @property
    def severity(self):
        return self["severity"]

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name not in self:
            raise AttributeError
        return super().__setattr__(name, value)

    def __getattribute__(self, name: str, /) -> Any:
        return super().__getattribute__(name)


class Resource(dict):
    def __init__(
        self,
        resource: str,
        module: str,
        id=None,
        source=None,
        first_seen=None,
        last_seen=None,
    ):
        dict.__init__(
            self,
            resource=resource,
            module=module,
            id=id,
            source=source,
            first_seen=first_seen,
            last_seen=last_seen,
        )

    @property
    def resource(self) -> str:
        return self["resource"]

    @property
    def module(self):
        return self["module"]

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name not in self:
            raise AttributeError
        return super().__setattr__(name, value)

    def __getattribute__(self, name: str, /) -> Any:
        return super().__getattribute__(name)

    @staticmethod
    def from_target(target: ConfigTarget):
        return Resource(target.resource, target.module)

    @staticmethod
    def from_discovery(discovery: Discovery):
        return Resource(discovery.resource, discovery.module, source=discovery.source)


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
