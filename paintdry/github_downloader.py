import os
import json
import sys
import requests_cache
from datetime import timedelta, datetime
from time import sleep
from utils import user_error, mkdir, rm_rf, cmd

from trivy import trivy_scan


class GithubSession:

    def __init__(self, token, cache_folder):
        self.session = requests_cache.CachedSession(
            os.path.join(cache_folder, "http_cache"), expire_after=timedelta(hours=2)
        )
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get(self, url):
        print("GET: " + url)
        r = self.session.get(url)
        if getattr(r, "from_cache", False):
            print("CACHE HIT: " + url)
        else:
            sleep(0.2)
            if r.status_code != 200:
                print(str(r.text))
                print(str(r.status_code))
                sleep(0.8)
        assert r.status_code == 200
        result = r.json()
        return result


def github_repo_info(session: GithubSession, organizations):
    repos = {}
    repos["github.com"] = {}
    for org in organizations:
        repos["github.com"][org] = {}
        for i in range(1, 10):
            data = session.get(
                f"https://api.github.com/orgs/{org}/repos?per_page=100&page={i}"
            )
            if not data:
                break
            for repo in data:
                name = repo["name"]
                if repo["visibility"] == "public" and not repo["archived"]:
                    rulesets = session.get(
                        f"https://api.github.com/repos/{org}/{name}/rulesets?per_page=100&page=1"
                    )
                    repo["rulesets"] = rulesets
                repos["github.com"][org][name] = repo
    return repos


def record_org_metadata(path, org, repos):
    data = {"repos": sorted(repos)}
    with open(path + "/org-metadata.json", "w") as f:
        f.write(json.dumps(data, indent=2))
        f.write("\n")


def get_secrets(secrets_json):
    try:
        st = os.stat(secrets_json)
    except FileNotFoundError:
        print("Warning: Secrets file missing - skipping downloads...")
        sys.exit(0)

    assert st is not None

    oct_perm = str(oct(st.st_mode))[-3:]
    if oct_perm != "600":
        user_error("Permissions of " + secrets_json + " must be 600, not " + oct_perm)
    try:
        with open(secrets_json, "r") as f:
            secrets = json.loads(f.read())
    except Exception as e:
        user_error(f"Something went wrong while reading {secrets_json}: '{str(e)}'")

    if not isinstance(secrets, dict):
        user_error(f"{secrets_json} must contain a JSON object")

    if not secrets.get("github_username"):
        user_error("Missing secret: github_username")
    if not secrets.get("github_access_token"):
        user_error("Missing secret: github_access_token")
    if not secrets.get("github_organizations"):
        user_error("Missing secret: github_organizations")

    return secrets


def download_repos(secrets_json, root, cache_folder):
    secrets = get_secrets(secrets_json)
    username = secrets["github_username"]
    token = secrets["github_access_token"]
    organizations = secrets["github_organizations"]

    github_session = GithubSession(token, cache_folder)

    data = github_repo_info(github_session, organizations)

    mkdir(f"{root}")
    mkdir(f"{root}/trivy-results")
    # TODO: Get trusted path from config
    trusted_path = (
        os.path.abspath(
            f"{root}/github.com/NorthernTechHQ/mystiko/branches/master/.pub-keys"
        )
        + "/"
    )
    if not os.path.exists(trusted_path):
        trusted_path = None
    # assert trusted_path is not None, "Trusted path is not set"
    for website, organizations in data.items():
        path = os.path.join(root, website)
        mkdir(path)
        for org, repos in organizations.items():
            path = os.path.join(root, website, org)
            mkdir(path)
            record_org_metadata(path, org, repos)
            for reponame, repo in repos.items():
                if repo.get("archived") == True:
                    # print("Skipping archived repo - " + reponame)
                    path = os.path.join(root, website, org, reponame)
                    if not os.path.exists(path):
                        mkdir(path)
                    if os.path.exists(f"{path}/branches"):
                        rm_rf(f"{path}/branches")
                    if os.path.exists(f"{path}/metadata.json"):
                        rm_rf(f"{path}/metadata.json")
                    if os.path.exists(f"{path}/update"):
                        rm_rf(f"{path}/update")
                    if not os.path.exists(f"{path}/archived"):
                        cmd(f"touch '{path}/archived'")
                    continue

                ts_path = os.path.join(root, website, org, reponame, "updated")
                if os.path.exists(ts_path):
                    with open(ts_path, "r") as f:
                        data = f.read().strip()
                        updated = datetime.fromisoformat(data)
                        now = datetime.now()
                        delta = now - updated
                        if delta < timedelta(hours=2):
                            # print("Skipping up-to-date repo " + reponame)
                            continue

                path = os.path.join(root, website, org, reponame)
                mkdir(path)
                path = os.path.join(root, website, org, reponame, "branches")
                mkdir(path)
                path = os.path.join(root, website, org, reponame, "metadata.json")
                with open(path, "w") as f:
                    f.write(json.dumps(repo, indent=2))
                default_branch = repo["default_branch"]
                default_branch_path = os.path.join(
                    root, website, org, reponame, "branches", default_branch
                )
                clone_path = (
                    f"https://{username}:{token}@{website}/{org}/{reponame}.git"
                )
                clone_cmd = f"git clone --recurse-submodules --single-branch --shallow-submodules -b {default_branch} {clone_path} {default_branch_path}"
                pull_cmd = f"sh -c 'cd {default_branch_path} && git pull origin {default_branch}'"
                unshallow_cmd = (
                    f"sh -c 'cd {default_branch_path} && git fetch --unshallow'"
                )
                remove_remote_cmd = f"sh -c 'cd {default_branch_path} && git remote | grep -q origin && git remote remove origin'"
                add_remote_cmd = f"sh -c 'cd {default_branch_path} && git remote add origin {clone_path}'"
                if not os.path.exists(default_branch_path):
                    cmd(clone_cmd, token=token)
                    sleep(2)
                    cmd(remove_remote_cmd, fail_ok=True)
                else:
                    cmd(remove_remote_cmd, fail_ok=True)
                    cmd(add_remote_cmd, token=token)
                    cmd(pull_cmd)
                    sleep(1)
                    cmd(remove_remote_cmd, fail_ok=True)

                # TODO: Checkout tags and branches and run trivy for each (after some filtering).

                if not os.path.exists(default_branch_path):
                    # TODO handle empty repos
                    continue

                trivy_scan(os.path.join(root, website, org, reponame), default_branch_path)

                if (
                    cmd(
                        f"sh -c 'cd {default_branch_path} && git rev-parse --is-shallow-repository'"
                    ).stdout.strip()
                    == "true"
                ):
                    cmd(remove_remote_cmd, fail_ok=True)
                    cmd(add_remote_cmd, token=token)
                    cmd(unshallow_cmd)
                    sleep(2)
                    cmd(remove_remote_cmd, fail_ok=True)
                tags = cmd(
                    f"sh -c 'cd {default_branch_path} && git show-ref --tags'",
                    fail_ok=True,
                ).stdout

                if tags:
                    tag_data = {}
                    sha_length = len("d9028fceac74241e743fc4d1d832cb4662e976eb")
                    separator = " refs/tags/"
                    expected_length = sha_length + len(separator) + 1
                    for line in tags.split("\n"):
                        line = line.strip()
                        if not line or len(line) < expected_length:
                            continue
                        if not line[sha_length:].startswith(separator):
                            continue
                        tag = line[expected_length - 1 :]
                        sha = line[0:sha_length]
                        tag_data[tag] = sha

                    if tag_data:
                        path = os.path.join(root, website, org, reponame, "tags.json")
                        with open(path, "w") as f:
                            f.write(json.dumps(tag_data, indent=2))

                # TODO GLRP:
                # if trusted_path:
                #     glrp_cmd = f"sh -c 'cd {default_branch_path} && glrp --trusted {trusted_path} --compare 5d && mv .before.json ../../ && mv .after.json ../../'"
                #     cmd(glrp_cmd)
                now = datetime.now()
                with open(ts_path, "w") as f:
                    f.write(now.isoformat() + "\n")


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: github_downloader.py <secrets.json> <target_folder> <cache_folder>"
        )
        sys.exit(1)

    secrets_json = sys.argv[1]
    target_folder = sys.argv[2]
    cache_folder = sys.argv[3]

    download_repos(secrets_json, target_folder, cache_folder)


if __name__ == "__main__":
    main()
