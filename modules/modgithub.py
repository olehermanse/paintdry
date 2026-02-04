import datetime
from functools import cache
from collections.abc import Iterable
from modlib import ModBase, strip_prefix, now, TAG_REGEX
import os
import json

@cache
def normalize_github(url: str) -> str:
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

    def discover_repos(self, request) -> Iterable[dict]:
        org = normalize_github(request["resource"])
        assert "/" not in org
        folder = f"mount-state/repos/github.com/{org}"
        if not os.path.exists(folder):
            return
        yield {
            "operation": "discovery",
            "resource": normalize_github(request["resource"]),
            "module": "github",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }

        for entry in os.scandir(folder):
            if not entry.is_dir():
                continue
            resource = org + "/" + entry.name
            if not os.path.exists(entry.path + "/metadata.json"):
                continue
            yield {
                "operation": "discovery",
                "resource": resource,
                "module": "github",
                "source": request["resource"],
                "timestamp": request["timestamp"],
            }

    def discovery(self, request: dict) -> Iterable[dict]:
        resource = normalize_github(request["resource"])
        if not "/" in resource:
            yield from self.discover_repos(request)
            return
        yield {
            "operation": "discovery",
            "resource": resource,
            "module": "github",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }

    def observation_org(self, request: dict) -> Iterable[dict]:
        org = normalize_github(request["resource"])
        folder = f"mount-state/repos/github.com/{org}"
        if not os.path.exists(folder):
            return
        yield {
            "operation": "observation",
            "resource": org,
            "module": "github",
            "attribute": "url",
            "value": f"https://github.com/{org}",
            "timestamp": now(),
            "severity": "none",
        }

        org_metadata = folder + "/org-metadata.json"
        if os.path.isfile(org_metadata):
            with open(org_metadata, "r") as f:
                org_metadata = json.loads(f.read())
            if "repos" in org_metadata:
                yield {
                    "operation": "observation",
                    "resource": org,
                    "module": "github",
                    "attribute": "repos",
                    "value": json.dumps(org_metadata["repos"]),
                    "timestamp": now(),
                    "severity": (
                        "none" if len(org_metadata["repos"]) > 0 else "high"
                    ),
                }

    def observation_repo(self, request: dict) -> Iterable[dict]:
        repo = normalize_github(request["resource"])
        folder = f"mount-state/repos/github.com/{repo}"
        if not os.path.exists(folder):
            return
        if os.path.exists(folder + "/archived"):
            yield {
                "operation": "observation",
                "resource": repo,
                "module": "github",
                "attribute": "archived",
                "value": True,
                "timestamp": now(),
                "severity": "none",
            }
            return
        # TODO: This is likely because of the empty repos and should be handled elsewhere
        if not os.path.exists(folder + "/updated"):
            return
        with open(folder + "/updated", "r") as f:
            ts = datetime.datetime.fromisoformat(f.read().strip())
            timestamp = int(ts.timestamp())
        with open(folder + "/metadata.json", "r") as f:
            data = json.loads(f.read())

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
            yield {
                "operation": "observation",
                "resource": repo,
                "module": "github",
                "attribute": name,
                "value": data.get(key, ""),
                "timestamp": timestamp,
                "severity": "none",
            }
        if "license" in data and data["license"]:
            yield {
                "operation": request["operation"],
                "resource": repo,
                "module": "github",
                "attribute": "license",
                "value": data["license"]["name"],
                "timestamp": timestamp,
                "severity": "none",
            }
        rulesets = "none"
        severity = "recommendation"
        if "rulesets" in data:
            rulesets = []
            for rule in data["rulesets"]:
                rulesets.append(rule["name"])
            if len(rulesets) > 0:
                severity = "none"
            rulesets = sorted(rulesets)
            rulesets = json.dumps(rulesets)
            yield {
                "operation": request["operation"],
                "resource": repo,
                "module": "github",
                "attribute": "rulesets",
                "value": rulesets,
                "timestamp": timestamp,
                "severity": severity,
            }

        for attribute, value in data.get("security_and_analysis", {}).items():
            status = value.get("status", "")
            severity = "none"
            if status == "disabled" and attribute in (
                "secret_scanning",
                "dependabot_security_updates",
                "secret_scanning_push_protection",
            ):
                severity = "recommendation"
            yield {
                "operation": request["operation"],
                "resource": repo,
                "module": "github",
                "attribute": attribute,
                "value": status,
                "timestamp": timestamp,
                "severity": severity,
            }

        tag_data = folder + "/tags.json"
        if os.path.isfile(tag_data):
            with open(tag_data, "r") as f:
                tag_data = json.loads(f.read())
                for tag, sha in tag_data.items():
                    if not TAG_REGEX.fullmatch(tag):
                        continue
                    yield {
                        "operation": "observation",
                        "resource": repo,
                        "module": "github",
                        "attribute": "tag:" + tag,
                        "value": sha,
                        "timestamp": now(),
                        "severity": "none",
                    }

    def observation(self, request: dict) -> Iterable[dict]:
        resource = normalize_github(request["resource"])
        if not "/" in resource:
            yield from self.observation_org(request)
            return
        yield from self.observation_repo(request)

    def change(self, request: dict) -> Iterable[dict]:
        assert request["old_value"] != request["new_value"]
        request["severity"] = "none"
        if request["attribute"] == "visibility":
            request["severity"] = "high"
        yield request


if __name__ == "__main__":
    module = ModGitHub()
    module.main()
