import datetime
from functools import cache
from modlib import ModBase, strip_prefix, now
import os
import json
import re

TAG_REGEX = re.compile(r"v?\d+\.\d+\.\d+(-\d+)?")

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
        observations = []
        observations.append(
            {
                "operation": request["operation"],
                "resource": org,
                "module": "github",
                "attribute": "url",
                "value": f"https://github.com/{org}",
                "timestamp": now(),
                "severity": "none",
            }
        )

        org_metadata = folder + "/org-metadata.json"
        if os.path.isfile(org_metadata):
            with open(org_metadata, "r") as f:
                org_metadata = json.loads(f.read())
            if "repos" in org_metadata:
                observations.append(
                    {
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
                )
        return observations

    def observation_repo(self, request: dict) -> list[dict]:
        repo = normalize_resource(request["resource"])
        folder = f"mount-state/repos/github.com/{repo}"
        if not os.path.exists(folder):
            return []
        if os.path.exists(folder + "/archived"):
            return [
                {
                    "operation": request["operation"],
                    "resource": repo,
                    "module": "github",
                    "attribute": "archived",
                    "value": True,
                    "timestamp": now(),
                    "severity": "none",
                }
            ]
        # TODO: This is likely because of the empty repos and should be handled elsewhere
        if not os.path.exists(folder + "/updated"):
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
                    "value": data.get(key, ""),
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
            observations.append(
                {
                    "operation": request["operation"],
                    "resource": repo,
                    "module": "github",
                    "attribute": "rulesets",
                    "value": rulesets,
                    "timestamp": timestamp,
                    "severity": severity,
                }
            )

        for attribute, value in data.get("security_and_analysis", {}).items():
            status = value.get("status", "")
            severity = "none"
            if status == "disabled" and attribute in (
                "secret_scanning",
                "dependabot_security_updates",
                "secret_scanning_push_protection",
            ):
                severity = "recommendation"
            observations.append(
                {
                    "operation": request["operation"],
                    "resource": repo,
                    "module": "github",
                    "attribute": attribute,
                    "value": status,
                    "timestamp": timestamp,
                    "severity": severity,
                }
            )

        tag_data = folder + "/tags.json"
        if os.path.isfile(tag_data):
            with open(tag_data, "r") as f:
                tag_data = json.loads(f.read())
                for tag, sha in tag_data.items():
                    if not TAG_REGEX.fullmatch(tag):
                        continue
                    observations.append(
                        {
                            "operation": "observation",
                            "resource": repo,
                            "module": "github",
                            "attribute": "tag:" + tag,
                            "value": sha,
                            "timestamp": now(),
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
        assert request["old_value"] != request["new_value"]
        request["severity"] = "none"
        if request["attribute"] == "visibility":
            request["severity"] = "high"
        return [request]


if __name__ == "__main__":
    module = ModGitHub()
    module.main()
