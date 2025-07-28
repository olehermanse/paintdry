import os
import json
import sys
import requests
import requests_cache
import subprocess
from datetime import timedelta, datetime
from time import sleep

token = None


def github_get(url):
    global token
    print("GET: " + url)
    r = requests.get(
        url,
        headers={
            "Authorization": f"token {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    if r.from_cache:
        print("CACHE HIT: " + url)
    if not r.from_cache:
        sleep(0.2)
        if r.status_code != 200:
            print(str(r.text))
            print(str(r.status_code))
            sleep(0.8)
    assert r.status_code == 200
    result = r.json()
    # print(result)
    return result


def github_repo_info(repos, organizations):
    repos["github.com"] = {}
    for org in organizations:
        repos["github.com"][org] = {}
        for i in range(1, 10):
            data = github_get(
                f"https://api.github.com/orgs/{org}/repos?per_page=100&page={i}"
            )
            if not data:
                break
            for repo in data:
                name = repo["name"]
                if repo["visibility"] == "public" and not repo["archived"]:
                    rulesets = github_get(
                        f"https://api.github.com/repos/{org}/{name}/rulesets?per_page=100&page=1"
                    )
                    repo["rulesets"] = rulesets
                repos["github.com"][org][name] = repo


def record_org_metadata(path, org, repos):
    data = {"repos": []}
    for name, repo in repos.items():
        data["repos"].append(name)
    data["repos"] = sorted(data["repos"])
    with open(path + "/org-metadata.json", "w") as f:
        f.write(json.dumps(data, indent=2))
        f.write("\n")


def mkdir(path):
    os.makedirs(path, exist_ok=True)


def cmd(cmd):
    global token
    print("CMD: " + cmd.replace(token, "TOKEN"))
    os.system(cmd)


def cmd_exitcode(cmd):
    global token
    print("CMD: " + cmd.replace(token, "TOKEN"))
    return os.system(cmd)


def cmd_stdout(cmd):
    global token
    print("CMD: " + cmd.replace(token, "TOKEN"))
    return subprocess.check_output(cmd, shell=True)


def user_error(message):
    print("Error: " + message)
    sys.exit(1)


def env_var(key):
    r = os.getenv(key)
    if not r:
        user_error("Environment variable missing: " + key)
    return r


def main():
    if len(sys.argv) != 4:
        print(
            "Usage: github_downloader.py <secrets.json> <target_folder> <cache_folder>"
        )
        sys.exit(1)

    secrets_json = sys.argv[1]
    root = sys.argv[2]
    cache_folder = sys.argv[3]

    requests_cache.install_cache(
        cache_folder + "http_cache", expire_after=timedelta(hours=2)
    )

    st = os.stat(secrets_json)
    oct_perm = str(oct(st.st_mode))[-3:]
    if oct_perm != "600":
        user_error("Permissions of " + secrets_json + "must be 600, not " + oct_perm)
    with open(secrets_json, "r") as f:
        secrets = json.loads(f.read())
    if not secrets.get("github_username"):
        user_error("Missing secret: github_username")
    if not secrets.get("github_access_token"):
        user_error("Missing secret: github_access_token")
    if not secrets.get("github_organizations"):
        user_error("Missing secret: github_organizations")
    username = secrets["github_username"]
    global token
    token = secrets["github_access_token"]
    organizations = secrets["github_organizations"]
    data = {}
    github_repo_info(data, organizations)
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
    assert trusted_path is not None, "Trusted path is not set"
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
                        cmd(f"rm -rf '{path}/branches'")
                    if os.path.exists(f"{path}/metadata.json"):
                        cmd(f"rm -rf '{path}/metadata.json'")
                    if os.path.exists(f"{path}/update"):
                        cmd(f"rm -rf '{path}/update'")
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
                pull_cmd = f"sh -c 'cd {default_branch_path} && git pull'"
                unshallow_cmd = (
                    f"sh -c 'cd {default_branch_path} && git fetch --unshallow'"
                )
                if not os.path.exists(default_branch_path):
                    cmd(clone_cmd)
                    sleep(2)
                else:
                    cmd(pull_cmd)
                    sleep(1)
                if (
                    cmd_stdout(
                        f"sh -c 'cd {default_branch_path} && git rev-parse --is-shallow-repository'"
                    )
                    == "true"
                ):
                    cmd(unshallow_cmd)
                    sleep(2)

                if trusted_path:
                    glrp_cmd = f"sh -c 'cd {default_branch_path} && glrp --trusted {trusted_path} --compare 5d && mv .before.json ../../ && mv .after.json ../../'"
                    cmd(glrp_cmd)
                now = datetime.now()
                with open(ts_path, "w") as f:
                    f.write(now.isoformat() + "\n")


if __name__ == "__main__":
    main()
