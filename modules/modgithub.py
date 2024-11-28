from pathlib import Path
from functools import cache
from modlib import ModBase, strip_prefix, now


@cache
def normalize_org(url: str) -> str:
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

    def discovery(self, request: dict) -> list[dict]:
        return [
            {
                "operation": "discovery",
                "resource": normalize_org(request["resource"]),
                "module": "github",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        ]

    def observation(self, request: dict) -> list[dict]:
        org = normalize_org(request["resource"])
        return [
            {
                "operation": request["operation"],
                "resource": org,
                "module": "github",
                "attribute": "url",
                "value": f"https://github.com/{org}",
                "timestamp": now(),
            }
        ]


if __name__ == "__main__":
    module = ModGitHub()
    module.main()
