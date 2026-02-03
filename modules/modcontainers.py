"""Warning: This module is very slow and probably not ready yet.
Need to find an efficient / slow way to sync with docker
without hitting rate limits."""
import json
import os
import subprocess
import tempfile
from functools import cache
from time import sleep

import requests

from modlib import ModBase, now, respond_with_severity, TAG_REGEX


@cache
def skopeo_list_tags(image: str) -> tuple[int, list[str]]:
    """List all tags for a container image using skopeo."""
    sleep(1)
    try:
        result = subprocess.run(
            ["skopeo", "list-tags", f"docker://{image}"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            return (now(), [])
        data = json.loads(result.stdout)
        return (now(), sorted(data.get("Tags", [])))
    except Exception:
        return (now(), [])


def skopeo_sync_with_digests(image: str, tags: list[str]) -> dict[str, str]:
    """
    Sync specific tags and return a dict mapping tag -> digest.
    Uses skopeo sync with --digestfile for efficiency.
    """
    if not tags:
        return {}

    digests = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        dest_dir = os.path.join(tmpdir, "images")
        digestfile = os.path.join(tmpdir, "digests.txt")
        yaml_file = os.path.join(tmpdir, "sync.yaml")

        # Parse image into registry and repository
        parts = image.split("/", 1)
        if len(parts) != 2:
            return {}
        registry, repository = parts

        # Create YAML config for skopeo sync with specific tags
        yaml_content = {registry: {repository: tags}}

        with open(yaml_file, "w") as f:
            # Write simple YAML manually to avoid dependency
            f.write(f"{registry}:\n")
            f.write(f"  images:\n")
            f.write(f"    {repository}:\n")
            for tag in tags:
                f.write(f"      - {tag}\n")

        try:
            result = subprocess.run(
                [
                    "skopeo",
                    "sync",
                    "--src",
                    "yaml",
                    "--dest",
                    "dir",
                    "--scoped",
                    "--digestfile",
                    digestfile,
                    yaml_file,
                    dest_dir,
                ],
                capture_output=True,
                text=True,
                timeout=600,
            )

            if result.returncode != 0:
                print(f"skopeo sync failed: {result.stderr}")
                return {}

            # Parse digestfile - format is "digest image-reference" per line
            if os.path.exists(digestfile):
                with open(digestfile) as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split(" ", 1)
                        if len(parts) == 2:
                            digest, ref = parts
                            # Extract tag from reference (e.g., docker.io/org/repo:tag)
                            if ":" in ref:
                                tag = ref.rsplit(":", 1)[1]
                                digests[tag] = digest

        except subprocess.TimeoutExpired:
            print(f"skopeo sync timed out for {image}")
        except Exception as e:
            print(f"skopeo sync error: {e}")

    return digests


@cache
def dockerhub_list_repositories(namespace: str) -> tuple[int, list[str]]:
    """List all repositories for an organization/user on Docker Hub."""
    sleep(1)
    repositories = []
    url = f"https://hub.docker.com/v2/repositories/{namespace}/"

    try:
        while url:
            r = requests.get(url, timeout=30)
            if r.status_code != 200:
                return (now(), [])
            data = r.json()
            for repo in data.get("results", []):
                repo_name = repo.get("name", "")
                if repo_name:
                    repositories.append(repo_name)
            url = data.get("next")
            if url:
                sleep(0.5)
        return (now(), sorted(repositories))
    except Exception:
        return (now(), [])


def parse_resource(resource: str) -> tuple[str, str | None]:
    """
    Parse a resource into (registry/namespace, image_name).

    Examples:
        "docker.io/cfengine" -> ("docker.io/cfengine", None)  # org only
        "docker.io/cfengine/cfengine" -> ("docker.io/cfengine", "cfengine")  # org + image
        "docker.io/library/nginx" -> ("docker.io/library", "nginx")  # official image
    """
    parts = resource.split("/")
    if len(parts) == 2:
        # docker.io/namespace - organization only
        return (resource, None)
    elif len(parts) == 3:
        # docker.io/namespace/image - specific image
        return (f"{parts[0]}/{parts[1]}", parts[2])
    else:
        # Unexpected format, treat as-is
        return (resource, None)


class ModContainers(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "docker.io/mendersoftware",
                "module": "containers",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "docker.io/mendersoftware/gui",
                "module": "containers",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> list[dict]:
        resource = request["resource"]
        registry_namespace, image = parse_resource(resource)

        discoveries = [
            {
                "operation": "discovery",
                "resource": resource,
                "module": "containers",
                "source": request["source"],
                "timestamp": request["timestamp"],
            }
        ]

        if image is None:
            # Resource is an organization - discover all repositories
            # Extract namespace from registry/namespace format
            parts = registry_namespace.split("/")
            if len(parts) == 2:
                registry, namespace = parts
                timestamp, repos = dockerhub_list_repositories(namespace)
                for repo in repos:
                    discoveries.append(
                        {
                            "operation": "discovery",
                            "resource": f"{registry_namespace}/{repo}",
                            "module": "containers",
                            "source": "containers",
                            "timestamp": request["timestamp"],
                        }
                    )

        return discoveries

    def observation(self, request: dict) -> list[dict]:
        assert request["module"] == "containers"

        resource = request["resource"]
        registry_namespace, image = parse_resource(resource)

        # Can only observe specific images, not organizations
        if image is None:
            return []

        observations = []
        timestamp = now()

        # Get all tags for the image
        _, tags = skopeo_list_tags(resource)

        # Filter tags using TAG_REGEX
        version_tags = [tag for tag in tags if TAG_REGEX.fullmatch(tag)]

        if not version_tags:
            return []

        # Sync all matching tags at once and get digests
        digests = skopeo_sync_with_digests(resource, version_tags)

        for tag in version_tags:
            digest = digests.get(tag, "")
            observations.append(
                {
                    "operation": request["operation"],
                    "resource": resource,
                    "module": "containers",
                    "attribute": tag,
                    "value": digest,
                    "timestamp": timestamp,
                    "severity": "none" if digest else "high",
                }
            )

        return observations

    def change(self, request):
        return respond_with_severity(request, "medium")


def main():
    module = ModContainers()
    module.main()


if __name__ == "__main__":
    main()
