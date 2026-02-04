from collections.abc import Iterable
from modlib import ModBase, now


class ModExample(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "localhost",
                "source": "config.json",
                "module": "example",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "localhost",
                "module": "example",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> Iterable[dict]:
        if request["resource"] != "localhost":
            return
        yield {
            "operation": "discovery",
            "resource": request["resource"],
            "module": "example",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }

    def observation(self, request: dict) -> Iterable[dict]:
        if request["resource"] != "localhost":
            return
        yield {
            "operation": "observation",
            "resource": request["resource"],
            "module": "example",
            "attribute": "now",
            "value": now(),
            "timestamp": now(),
            "severity": "none",
        }


def main():
    mod = ModExample()
    mod.main()


if __name__ == "__main__":
    main()
