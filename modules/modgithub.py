import datetime
from functools import cache
from modlib import ModBase, strip_prefix, now
import os
import json


@cache
def normalize_resource(url: str) -> str:
    while url.endswith("/"):
        url = url[0:-1]
    url = strip_prefix("http://", url)
    url = strip_prefix("https://", url)
    url = strip_prefix("www.", url)
    url = strip_prefix("github.com/", url)
    return url


class ModGitHub(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "cfengine",
                "source": "config.json",
                "module": "github",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "cfengine",
                "module": "github",
                "timestamp": 1730241747,
            },
        ]

    def discover_repos(self, request):
        org = normalize_resource(request["resource"])
        assert "/" not in org
        folder = f"mount-state/repos/github.com/{org}"
        if not os.path.exists(folder):
            return []
        discoveries = [
            {
                "operation": "discovery",
                "resource": normalize_resource(request["resource"]),
                "module": "github",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        ]

        for entry in os.scandir(folder):
            if not entry.is_dir():
                continue
            resource = org + "/" + entry.name
            if not os.path.exists(entry.path + "/metadata.json"):
                continue
            discoveries.append(
                {
                    "operation": "discovery",
                    "resource": resource,
                    "module": "github",
                    "source": request["resource"],
                    "timestamp": request["timestamp"],
                }
            )

        return discoveries

    def discovery(self, request: dict) -> list[dict]:
        resource = normalize_resource(request["resource"])
        if not "/" in resource:
            return self.discover_repos(request)
        return [
            {
                "operation": "discovery",
                "resource": resource,
                "module": "github",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        ]

    def observation_org(self, request: dict) -> list[dict]:
        org = normalize_resource(request["resource"])
        folder = f"mount-state/repos/github.com/{org}"
        if not os.path.exists(folder):
            return []
        return [
            {
                "operation": request["operation"],
                "resource": org,
                "module": "github",
                "attribute": "url",
                "value": f"https://github.com/{org}",
                "timestamp": now(),
                "severity": "none",
            }
        ]

    def observation_repo(self, request: dict) -> list[dict]:
        repo = normalize_resource(request["resource"])
        folder = f"mount-state/repos/github.com/{repo}"
        if not os.path.exists(folder):
            return []
        with open(folder + "/updated", "r") as f:
            ts = datetime.datetime.fromisoformat(f.read().strip())
            timestamp = int(ts.timestamp())
        with open(folder + "/metadata.json", "r") as f:
            data = json.loads(f.read())

        observations = []
        keys = {
            "html_url": "url",
            "description": "description",
            "default_branch": "default_branch",
            "visibility": "visibility",
            "archived": "archived",
            "homepage": "homepage",
        }
        for key, name in keys.items():
            if key not in data:
                continue
            observations.append(
                {
                    "operation": request["operation"],
                    "resource": repo,
                    "module": "github",
                    "attribute": name,
                    "value": data[key],
                    "timestamp": timestamp,
                    "severity": "none",
                }
            )
        if "license" in data and data["license"]:
            observations.append(
                {
                    "operation": request["operation"],
                    "resource": repo,
                    "module": "github",
                    "attribute": "license",
                    "value": data["license"]["name"],
                    "timestamp": timestamp,
                    "severity": "none",
                }
            )
        return observations

    def observation(self, request: dict) -> list[dict]:
        resource = normalize_resource(request["resource"])
        if not "/" in resource:
            return self.observation_org(request)
        return self.observation_repo(request)

    def change(self, request: dict) -> list[dict]:
        # resource
        # module
        # attribute
        # old_value
        # new_value
        # timestamp
        assert request["old_value"] != request["new_value"]
        request["severity"] = "none"
        if request["attribute"] == "visibility":
            request["severity"] = "high"
        return [request]


if __name__ == "__main__":
    module = ModGitHub()
    module.main()
