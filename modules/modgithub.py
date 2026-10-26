import datetime
from concurrent.futures import ThreadPoolExecutor
from functools import cache
from collections.abc import Iterable
from modlib import ModBase, strip_prefix, now
from glrp.internal_parser import parse as parse_git_log
import glob
import io
import os
import re
import shutil
import subprocess
import sys
import json
import tempfile
import time
import requests

HOUR = 60 * 60
# Don't try GitHub again until this long after rate limiting / server errors:
ABORT_TIMEOUT = 1 * HOUR
# Repos pulled more recently than this are answered from disk without pulling:
FRESH_TIMEOUT = 2 * HOUR
# Background jobs (tags, trivy) after a repo is cloned / pulled, these run
# in parallel with cloning. Only 1, parallel trivy runs fight over the trivy
# cache lock and fail:
PROCESSING_THREADS = 1
SHA_LENGTH = len("d9028fceac74241e743fc4d1d832cb4662e976eb")
# Tags / branches we generate SBOMs for (the default branch is always included),
# e.g. main, production, v1, v1.2, v1.2.3-1, 3.27.x:
SBOM_REF_REGEX = re.compile(
    r"master|main|production|staging|v?\d+(\.\d+){0,2}(\.x)?(-\d+)?"
)
CONFIG_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")
SECRETS_JSON = os.path.join(CONFIG_FOLDER, "secrets.json")
# The .pub-keys folder of mystiko, mounted in docker-compose.yml, with
# <name>.asc and <name>.fp (fingerprint) files in current_employees/ and
# ex_employees/:
PUB_KEYS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pub-keys")


class GitHubAbort(Exception):
    """Rate limiting or server error from GitHub, stop and try again later"""


def abort_timestamp_path(cache_folder):
    return os.path.join(cache_folder, "last_timestamp")


def get_last_abort_timestamp(cache_folder):
    """Return the epoch timestamp of the last abort, or None if there was none"""
    try:
        with open(abort_timestamp_path(cache_folder), "r") as f:
            return int(f.read().strip())
    except FileNotFoundError:
        return None


def write_abort_timestamp(cache_folder):
    with open(abort_timestamp_path(cache_folder), "w") as f:
        f.write(f"{now()}\n")


@cache
def normalize_github(url: str) -> str:
    while url.endswith("/"):
        url = url[0:-1]
    url = strip_prefix("http://", url)
    url = strip_prefix("https://", url)
    url = strip_prefix("www.", url)
    url = strip_prefix("github.com/", url)
    return url


def is_repo_observation(request: dict) -> bool:
    return request["operation"] == "observation" and "/" in normalize_github(
        request["resource"]
    )


def atomic_write(path, data):
    dirname = os.path.dirname(os.path.abspath(path))
    fd, tmp_path = tempfile.mkstemp(dir=dirname, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise


def cmd(command, token=None, fail_ok=False):
    def mask(s):
        return s.replace(token, "TOKEN") if token else s

    print("CMD: " + mask(command))
    r = subprocess.run(command, shell=True, capture_output=True, text=True)
    if r.stdout:
        print(mask(r.stdout), end="")
    if r.stderr:
        print(mask(r.stderr), end="", file=sys.stderr)
    if r.returncode != 0 and not fail_ok:
        print(f"Warning: Command exited with code {r.returncode}")
    return r


def rm_rf(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.remove(path)


def trivy_scan(path):
    """Return a CycloneDX SBOM (dict) for the files in path, or None"""
    try:
        result = subprocess.run(
            ["trivy", "fs", "--quiet", "--format", "cyclonedx", path],
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        print("Warning: trivy not found - skipping SBOM generation")
        return None
    if result.returncode != 0:
        print(f"Trivy scan failed for {path}: {result.stderr}")
        return None
    return json.loads(result.stdout)


def list_sboms(repo_path):
    """Yield (<branches|tags>/<name>, path) for each SBOM in <repo_path>/sboms"""
    sboms = os.path.join(repo_path, "sboms")
    for root, _, files in os.walk(sboms):
        if "sbom.json" in files:
            yield os.path.relpath(root, sboms), os.path.join(root, "sbom.json")


def write_sboms(repo_path, branch_path):
    """Check out each tag / branch in <repo_path>/sbom_target.json, and save
    their SBOMs in <repo_path>/sboms/<branches|tags>/<name>/sbom.json"""
    with open(os.path.join(repo_path, "sbom_target.json"), "r") as f:
        targets = json.loads(f.read())
    branch = os.path.relpath(branch_path, os.path.join(repo_path, "branches"))
    try:
        for kind, refs in targets.items():
            for name, sha in refs.items():
                # Fails if the fetch of sha failed, skip it:
                if cmd(f"sh -c 'cd {branch_path} && git checkout -qf {sha}'").returncode:
                    continue
                sbom = trivy_scan(branch_path)
                if sbom:
                    output = os.path.join(repo_path, "sboms", kind, name, "sbom.json")
                    os.makedirs(os.path.dirname(output), exist_ok=True)
                    atomic_write(output, sbom)
    finally:
        # -B also fixes the branch if a crash left HEAD detached (pull resets HEAD):
        cmd(f"sh -c 'cd {branch_path} && git checkout -qf -B {branch} {targets['branches'][branch]}'")
    # Tags / branches which are gone (or no longer match SBOM_REF_REGEX):
    wanted = {f"{kind}/{name}" for kind, refs in targets.items() for name in refs}
    # list(), so we don't delete folders while os.walk() is in them:
    for ref, path in list(list_sboms(repo_path)):
        if ref not in wanted:
            rm_rf(os.path.dirname(path))


def write_tags(repo_path, branch_path):
    tags = cmd(
        f"sh -c 'cd {branch_path} && git show-ref --tags'",
        fail_ok=True,
    ).stdout
    tag_data = {}
    separator = " refs/tags/"
    expected_length = SHA_LENGTH + len(separator) + 1
    for line in tags.split("\n"):
        line = line.strip()
        if not line or len(line) < expected_length:
            continue
        if not line[SHA_LENGTH:].startswith(separator):
            continue
        tag = line[expected_length - 1 :]
        sha = line[0:SHA_LENGTH]
        tag_data[tag] = sha
    # Also when empty, so deleting the last tags is noticed:
    with open(os.path.join(repo_path, "tags.json"), "w") as f:
        f.write(json.dumps(tag_data, indent=2))


def import_pub_keys():
    """Import the employees' public keys into gpg, so git log --show-signature
    can verify their signatures. Returns False if there are no keys."""
    keys = glob.glob(os.path.join(PUB_KEYS, "*_employees", "*.asc"))
    if not keys:
        print(f"Warning: No public keys in {PUB_KEYS} - skipping commit signatures")
        return False
    result = subprocess.run(
        ["gpg", "--batch", "--quiet", "--import", *keys],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Warning: Importing public keys failed: {result.stderr}")
    return True


def read_fingerprints(folder):
    """{fingerprint: name} from the <name>.fp files of folder, like glrp --trusted"""
    fingerprints = {}
    for path in glob.glob(os.path.join(folder, "*.fp")):
        name = os.path.basename(path)[: -len(".fp")]
        with open(path, "r") as f:
            for line in f.read().split("\n"):
                line = line.replace(" ", "")
                if line:
                    fingerprints[line] = name
    return fingerprints


@cache
def get_employee_domains():
    path = os.path.join(CONFIG_FOLDER, "config-override.json")
    if not os.path.isfile(path):
        path = os.path.join(CONFIG_FOLDER, "config.json")
    with open(path, "r") as f:
        config = json.load(f)
    return tuple(config["modules"]["github"].get("employee_domains", []))


def write_commit_signatures(repo_path, branch_path):
    """Count the signed commits of each key owner (<name>.fp in PUB_KEYS),
    and the unsigned / unknown key commits of each employee (committer email).
    Saved in <repo_path>/commit_signatures.json"""
    # Not whether they are current or ex employees, so the counts don't change
    # when an employee leaves (the key is moved to ex_employees/), see change():
    owners = {}
    for folder in ("current_employees", "ex_employees"):
        owners.update(read_fingerprints(os.path.join(PUB_KEYS, folder)))
    # Not cmd(), it would print the whole log:
    log = subprocess.run(
        ["git", "log", "--format=raw", "--show-signature"],
        cwd=branch_path,
        capture_output=True,
        text=True,
        errors="replace",
    )
    if log.returncode != 0:
        print(f"git log failed for {branch_path}: {log.stderr}")
        return
    signatures = {"signed": {}, "unsigned": {}, "unknown": {}, "offending_commits": {}}
    try:
        for commit in parse_git_log(io.StringIO(log.stdout), replace_errors=False):
            fingerprint = commit.get("fingerprint")
            # Anyone can make a signature which claims to be from a key, it
            # must also be verified (the key is imported):
            valid = commit.get("valid_signature", False)
            name = None
            if valid and fingerprint:
                # Some .fp files have the long key ID (the last 16 characters
                # of the fingerprint) instead of the whole fingerprint:
                name = owners.get(fingerprint, owners.get(fingerprint[-16:]))
            # Any committer email, also ex employees using another one:
            if name:
                signatures["signed"][name] = signatures["signed"].get(name, 0) + 1
                continue
            # The committer signs, not the author (e.g. GitHub signs merges):
            email = commit["committer"]["email"]
            if email.split("@")[-1] not in get_employee_domains():
                continue
            kind = "unknown" if fingerprint else "unsigned"
            signatures[kind][email] = signatures[kind].get(email, 0) + 1
            signatures["offending_commits"][commit["commit"]] = kind
    except Exception as e:
        # E.g. assertions in glrp for git output it doesn't understand:
        print(f"glrp failed for {branch_path}: {e!r}")
        return
    atomic_write(os.path.join(repo_path, "commit_signatures.json"), signatures)


def get_secrets(secrets_json):
    """Return secrets dict, or None if there are no secrets (offline mode)"""
    try:
        st = os.stat(secrets_json)
    except FileNotFoundError:
        print("Warning: Secrets file missing - answering from disk only")
        return None

    oct_perm = str(oct(st.st_mode))[-3:]
    if oct_perm != "600":
        sys.exit(f"Permissions of {secrets_json} must be 600, not {oct_perm}")
    with open(secrets_json, "r") as f:
        secrets = json.loads(f.read())

    if not isinstance(secrets, dict):
        sys.exit(f"{secrets_json} must contain a JSON object")
    for key in ("github_username", "github_access_token"):
        if not secrets.get(key):
            sys.exit(f"Missing secret: {key}")
    return secrets


class GithubSession:
    def __init__(self, token):
        # requests_cache.install_cache() (ModBase) makes this session cached
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"token {token}",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def get(self, url):
        """Return parsed JSON, None for 404, raise GitHubAbort on rate limiting / errors"""
        print("GET: " + url)
        r = self.session.get(url)
        if getattr(r, "from_cache", False):
            print("CACHE HIT: " + url)
        else:
            # Go slowly, never more than 1 request per second:
            time.sleep(1)
        if r.status_code == 200:
            return r.json()
        print(f"{r.status_code}: {r.text}")
        rate_limited = r.status_code == 429 or (
            r.status_code == 403
            and (
                r.headers.get("x-ratelimit-remaining") == "0"
                or "rate limit" in r.text.lower()
            )
        )
        # 401 is a bad / expired token, everything would fail, stop too:
        if rate_limited or r.status_code == 401 or r.status_code >= 500:
            raise GitHubAbort(f"{r.status_code} from {url}")
        # 404 or other 403 (e.g. no access to one repo), skip just this one:
        return None

class ModGitHub(ModBase):
    def __init__(self):
        super().__init__()
        # Set up from secrets.json in handle_files(), None means offline
        # (answer from what is already on disk):
        self.session = None

    def repo_folder(self, resource: str) -> str:
        # Repos are stored in <state folder>/repos/github.com/<org>/<repo>.
        # The state folder is passed as the third argument (cache_folder),
        # so this works regardless of the current working directory. Fall
        # back to a relative path when run manually (stdin / example mode)
        # from the repo root.
        state = self.cache_folder or "mount-state/"
        return os.path.join(state, "repos", "github.com", resource)

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
        if self.session is not None:
            self.download_org_metadata(org)
        folder = self.repo_folder(org)
        org_metadata = folder + "/org-metadata.json"
        if not os.path.isfile(org_metadata):
            return
        with open(org_metadata, "r") as f:
            org_metadata = json.loads(f.read())
        yield {
            "operation": "discovery",
            "resource": normalize_github(request["resource"]),
            "module": "github",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }

        for name in org_metadata.get("repos", []):
            if name in org_metadata.get("archived", []):
                continue
            if os.path.exists(os.path.join(folder, name, "archived")):
                continue
            resource = org + "/" + name
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
        folder = self.repo_folder(org)
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
        folder = self.repo_folder(repo)
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
            # All tags, not only versions, see change() for the severities:
            yield {
                "operation": "observation",
                "resource": repo,
                "module": "github",
                "attribute": "tags",
                "value": json.dumps(sorted(tag_data)),
                "timestamp": now(),
                "severity": "none",
            }
            for tag, sha in tag_data.items():
                yield {
                    "operation": "observation",
                    "resource": repo,
                    "module": "github",
                    "attribute": "tag:" + tag,
                    "value": sha,
                    "timestamp": now(),
                    "severity": "none",
                }
        if "releases" in data:
            yield {
                "operation": "observation",
                "resource": repo,
                "module": "github",
                "attribute": "releases",
                "value": json.dumps(data["releases"]),
                "timestamp": timestamp,
                "severity": "none",
            }
        signatures = folder + "/commit_signatures.json"
        # Employees should sign their commits in public repos, see change():
        if data.get("visibility") == "public" and os.path.isfile(signatures):
            with open(signatures, "r") as f:
                signatures = json.loads(f.read())
            yield {
                "operation": "observation",
                "resource": repo,
                "module": "github",
                "attribute": "commit_signatures",
                "value": json.dumps(signatures, sort_keys=True),
                "timestamp": timestamp,
                "severity": "none",
            }

        for ref, path in list_sboms(folder):
            with open(path, "r") as f:
                sbom = json.loads(f.read())
            # Same package can appear in multiple lockfiles, collect all versions
            dependencies = {}
            for component in sbom.get("components", []):
                purl = component.get("purl")
                if not purl:
                    # E.g. the lockfile itself (type "application")
                    continue
                name = purl.split("@")[0]
                dependencies.setdefault(name, set()).add(component.get("version", ""))
            for name, versions in dependencies.items():
                yield {
                    "operation": "observation",
                    "resource": repo,
                    "module": "github",
                    # E.g. dependency:tags/v1.2.3:pkg:npm/lodash, git
                    # doesn't allow ":" in ref names:
                    "attribute": f"dependency:{ref}:{name}",
                    "value": json.dumps(sorted(versions)),
                    "timestamp": timestamp,
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
        attribute = request["attribute"]
        request["severity"] = "none"
        # Tags shouldn't move, someone with access could point them to
        # malicious commits:
        if attribute == "visibility" or attribute.startswith("tag:"):
            request["severity"] = "high"
        elif attribute in ("tags", "releases"):
            # New ones are expected, deleted ones are not (also if as many
            # were created, so not just comparing lengths):
            deleted = set(request["old_value"]) - set(request["new_value"])
            request["severity"] = "high" if deleted else "notice"
        elif attribute == "commit_signatures":
            old = request["old_value"]
            new = request["new_value"]
            # Old commits can't be fixed, new unsigned / unknown key ones are
            # what we want to catch (fewer means the history was rewritten or
            # a key was added):
            added = set(new.get("offending_commits", {})) - set(
                old.get("offending_commits", {})
            )
            # Ex employees' keys shouldn't sign new commits. Checked now, not
            # when observed, so leaving doesn't change the observation:
            ex = set(read_fingerprints(os.path.join(PUB_KEYS, "ex_employees")).values())
            resigned = any(
                n > old.get("signed", {}).get(name, 0)
                for name, n in new.get("signed", {}).items()
                if name in ex
            )
            request["severity"] = "high" if added or resigned else "notice"
        yield request

    # Downloading from GitHub

    def secrets_file(self):
        return SECRETS_JSON

    def setup_github(self, secret_file):
        secrets = get_secrets(secret_file)
        if secrets is None:
            return
        self.username = secrets["github_username"]
        self.token = secrets["github_access_token"]
        self.session = GithubSession(self.token)

    def download_org_metadata(self, org):
        """List all repos in an org and write org-metadata.json (slow first time)"""
        repos = []
        archived = []
        for i in range(1, 10):
            data = self.session.get(
                f"https://api.github.com/orgs/{org}/repos?per_page=100&page={i}"
            )
            if not data:
                break
            for repo in data:
                repos.append(repo["name"])
                if repo["archived"]:
                    archived.append(repo["name"])
        folder = self.repo_folder(org)
        os.makedirs(folder, exist_ok=True)
        data = {"repos": sorted(repos), "archived": sorted(archived)}
        with open(folder + "/org-metadata.json", "w") as f:
            f.write(json.dumps(data, indent=2))
            f.write("\n")

    def read_last_updated(self, repo) -> int:
        path = os.path.join(self.repo_folder(repo), "updated")
        try:
            with open(path, "r") as f:
                ts = datetime.datetime.fromisoformat(f.read().strip())
                return int(ts.timestamp())
        except (FileNotFoundError, ValueError):
            return 0  # Never updated (or corrupt), treat as oldest

    def write_last_updated(self, repo):
        path = os.path.join(self.repo_folder(repo), "updated")
        # Atomic, the main thread may read it while we write it:
        tmp = path + ".tmp"
        with open(tmp, "w") as f:
            f.write(datetime.datetime.now().isoformat() + "\n")
        os.replace(tmp, path)

    def mark_archived(self, repo):
        path = self.repo_folder(repo)
        rm_rf(f"{path}/branches")
        rm_rf(f"{path}/metadata.json")
        rm_rf(f"{path}/updated")
        with open(f"{path}/archived", "w"):
            pass

    def clone_or_pull(self, repo):
        """Download metadata and clone / pull the repo (slow, talks to GitHub).

        Returns the path of the default branch checkout, or None if there is
        nothing more to process (archived, empty, deleted or failed).
        """
        path = self.repo_folder(repo)
        os.makedirs(path, exist_ok=True)

        info = self.session.get(f"https://api.github.com/repos/{repo}")
        if info is None:
            return None
        if info.get("archived"):
            self.mark_archived(repo)
            return None
        rm_rf(f"{path}/archived")
        if info.get("visibility") == "public":
            rulesets = self.session.get(
                f"https://api.github.com/repos/{repo}/rulesets?per_page=100&page=1"
            )
            if rulesets is not None:
                info["rulesets"] = rulesets
        releases = []
        for page in range(1, 10):
            data = self.session.get(
                f"https://api.github.com/repos/{repo}/releases?per_page=100&page={page}"
            )
            if data is None:
                # Incomplete, would look like deleted releases:
                releases = None
                break
            releases += [r["tag_name"] for r in data if not r["draft"]]
            if len(data) < 100:
                break
        if releases is not None:
            info["releases"] = sorted(releases)
        with open(f"{path}/metadata.json", "w") as f:
            f.write(json.dumps(info, indent=2))

        branch = info["default_branch"]
        branch_path = os.path.join(path, "branches", branch)
        os.makedirs(os.path.join(path, "branches"), exist_ok=True)
        url = f"https://{self.username}:{self.token}@github.com/{repo}.git"
        # Remove the remote after we're done, so the token isn't stored on disk:
        remove_remote = f"sh -c 'cd {branch_path} && git remote | grep -q origin && git remote remove origin'"
        add_remote = f"sh -c 'cd {branch_path} && git remote add origin {url}'"
        cloned = False
        if not os.path.exists(branch_path):
            cmd(
                f"git clone --recurse-submodules --single-branch --shallow-submodules -b {branch} {url} {branch_path}",
                token=self.token,
            )
            cloned = True

        if not os.path.exists(branch_path):
            # Empty repo or failed clone, metadata is still useful:
            self.write_last_updated(repo)
            return None

        # Remove first, git clone adds origin and a crashed run may have left it:
        cmd(remove_remote, fail_ok=True)
        cmd(add_remote, token=self.token)
        try:
            if not cloned:
                # Not git pull, it doesn't get new tags and fails on force
                # pushes. Moves and deletes (--prune) tags, so it's noticed,
                # --prune-tags doesn't work when the branch is given:
                fetch = cmd(
                    f"sh -c 'cd {branch_path} && git fetch --force --prune origin {branch} \"+refs/tags/*:refs/tags/*\"'",
                    token=self.token,
                )
                if fetch.returncode == 0:
                    cmd(f"sh -c 'cd {branch_path} && git reset -q --hard FETCH_HEAD'")
            is_shallow = cmd(
                f"sh -c 'cd {branch_path} && git rev-parse --is-shallow-repository'"
            ).stdout.strip()
            if is_shallow == "true":
                cmd(f"sh -c 'cd {branch_path} && git fetch --unshallow'", token=self.token)
            # After the reset, it records HEAD as the default branch's sha:
            self.fetch_sbom_targets(repo, branch_path, branch)
        finally:
            cmd(remove_remote, fail_ok=True)
        return branch_path

    def fetch_sbom_targets(self, repo, branch_path, branch):
        """Fetch the tags / branches matching SBOM_REF_REGEX (clone is single
        branch), and save them and the default branch in
        <repo>/sbom_target.json. The origin remote must be added."""
        refs = cmd(
            f"sh -c 'cd {branch_path} && git ls-remote --heads --tags origin'",
            token=self.token,
        ).stdout
        targets = {"branches": {}, "tags": {}}
        refspecs = []
        for line in refs.splitlines():
            sha, _, ref = line.partition("\t")
            _, kind, name = ref.split("/", 2)
            # Also skips the peeled annotated tags, <tag>^{}:
            if SBOM_REF_REGEX.fullmatch(name):
                targets["branches" if kind == "heads" else "tags"][name] = sha
                # Not into refs/remotes/origin/, those are deleted with the remote:
                refspecs.append(f"+{ref}:refs/sbom/{kind}/{name}")
        if refspecs:
            cmd(
                f"sh -c 'cd {branch_path} && git fetch -q --no-tags origin {' '.join(refspecs)}'",
                token=self.token,
            )
        head = cmd(f"sh -c 'cd {branch_path} && git rev-parse HEAD'").stdout.strip()
        targets["branches"][branch] = head
        atomic_write(os.path.join(self.repo_folder(repo), "sbom_target.json"), targets)

    def process_repo(self, repo, branch_path):
        """Background job after clone / pull, local only (no GitHub requests)"""
        path = self.repo_folder(repo)
        try:
            write_tags(path, branch_path)
            if self.pub_keys:
                write_commit_signatures(path, branch_path)
            write_sboms(path, branch_path)
            self.write_last_updated(repo)
        except Exception as e:
            print(f"Processing {repo} failed: {e}")

    # Request backlog

    def get_new_request_backlog(self, input_dir):
        """Read requests from folder, put them in backlog and delete files"""
        with os.scandir(input_dir) as it:
            names = [e.name for e in it if e.is_file() and e.name.endswith(".json")]
        for name in names:
            input_file = os.path.join(input_dir, name)
            try:
                with open(input_file, "r") as f:
                    data = json.loads(f.read())
            except json.JSONDecodeError as e:
                # Delete it anyway, otherwise we'd crash on it every run:
                print(f"Skipping malformed request file {name}: {e}")
                data = []
            if type(data) is dict:
                data = [data]
            self.request_backlog.extend(data)
            os.remove(input_file)

    def save_response(self, output_dir, results):
        if not results:
            return
        # pid, so 2 runs in the same second can't overwrite each other's files:
        filename = os.path.join(output_dir, f"{now()}-{os.getpid()}-{self.counter}.json")
        self.counter += 1
        atomic_write(filename, results)

    def is_ready(self, request) -> bool:
        """Repo observations wait until the repo is pulled and processed, the rest are ready"""
        if not is_repo_observation(request):
            return True
        repo = normalize_github(request["resource"])
        if repo in self.processing:
            future = self.processing[repo]
            return future is None or future.done()
        # Not pulled in this run, answer from disk if offline or recently pulled:
        return self.session is None or now() - self.read_last_updated(repo) < FRESH_TIMEOUT

    def handle_ready_requests(self, output_dir):
        """Answer and remove all requests in backlog which are ready"""
        remaining = []
        results = []
        # Discovery first, it may update org-metadata.json for org observations:
        for request in sorted(self.request_backlog, key=lambda r: r["operation"] != "discovery"):
            if self.is_ready(request):
                try:
                    results.extend(self.handle_request(request))
                except Exception as e:
                    # Drop it, bad data on disk shouldn't stop all other requests:
                    print(f"Failed to handle {request}: {e!r}")
            else:
                remaining.append(request)
        self.request_backlog = remaining
        self.save_response(output_dir, results)

    def pick_next_repo(self):
        repos = {}
        for request in self.request_backlog:
            if not is_repo_observation(request):
                continue
            repo = normalize_github(request["resource"])
            if repo in self.processing:
                continue
            repos[repo] = self.read_last_updated(repo)
        return min(repos, key=repos.get, default=None)

    def clone_one_repo(self):
        """Pick the repo with the oldest data from the backlog and download it.
        This function is slow / blocking, but after it is done downloading from
        GitHub, it starts a background job to do the rest of the processing.
        """
        repo = self.pick_next_repo()
        if repo is None:
            return
        self.processing[repo] = None  # Started, so we don't pick it again
        branch_path = self.clone_or_pull(repo)
        if branch_path is not None:
            self.processing[repo] = self.executor.submit(
                self.process_repo, repo, branch_path
            )

    # override
    def handle_files(self, input_dir, output_dir):
        assert os.path.isdir(input_dir)
        assert os.path.isdir(output_dir)

        last_abort = get_last_abort_timestamp(self.cache_folder)
        if last_abort is not None and now() - last_abort < ABORT_TIMEOUT:
            print("Sleeping to avoid unnecessary polling after error / rate limiting")
            return

        self.request_backlog = []
        # Repos we have cloned / pulled in this run, repo -> Future of the
        # background processing (None if there was nothing to process):
        self.processing = {}
        self.counter = 0

        self.get_new_request_backlog(input_dir)
        if not self.request_backlog:
            return
        self.setup_github(self.secrets_file())
        self.pub_keys = import_pub_keys()

        self.executor = ThreadPoolExecutor(max_workers=PROCESSING_THREADS)
        try:
            while self.request_backlog:
                self.handle_ready_requests(output_dir)
                self.clone_one_repo()
                self.handle_ready_requests(output_dir)
                if self.request_backlog:
                    time.sleep(1)
        except GitHubAbort as e:
            print(f"Stopping, will not try again for {ABORT_TIMEOUT}s: {e}")
            # Drop the remaining requests, what we already downloaded is
            # on disk and will be answered without pulling in the next run:
            write_abort_timestamp(self.cache_folder)
        finally:
            self.executor.shutdown(wait=True)


def main():
    mod = ModGitHub()
    mod.main()


if __name__ == "__main__":
    main()
