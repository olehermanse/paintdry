# GitHub module v2.0

## Goals

- Merge github_downloader.py and modgithub.py
- Downloading repos / using the GitHub API happens slowly (1s sleep between each request) and sequentially.
- After downloading a repo (pull / clone) we should process it in parallel (tags, trivy etc.)
- Requests for discovery and change are easy and should be answered fast, for example between every repo clone.
- Module should stop and quit when there is nothing more to clone (all repos are cloned, no more repos left to clone in this run).
- Module should stop and quit when it detects rate limiting or 500 internal server error from GitHub.
  - In that case, we should write down the timestamp and ensure we don't try again until 1 hour later.
- When module starts and builds up a queue of repos to clone, we want to prioritize the repos with the oldest data.
- The module should emit responses (results) as it's working, after every clone / pull there should be a burst of results coming out and being added to the database.
- In the future we will want to run more processing of the repos (similar to trivy).
- If the module receives 2 requests for the same resource (because it took too long to answer the first one), we can deduplicate them, keeping only the most recent request.
  Dropping some requests is okay, for example in the case of errors or rate limiting.
- If the module starts and there are 0 requests, it should be a no-op and exit.

## Requests

The module receives 3 types of requests:

- Discovery - Register resources in the database (from config and other modules).
  In the case of GitHub module, this should discover all repos in an org when a discovery request arrives for the org.
- Change - Sent to us by the updater when it detects a value has changed (new observation.value is different from old observation.value).
- Observation - The main requests to actually get results / observations.
  We get the name of the repo, and we respond with relevant values when we are done cloning and processing it.

The module can pick up (read) all of the requests from the folder and answer them in any order, as quickly or slowly as we want, when the actual data / processing is done.
After reading a request from disk we can delete the request so we don't re-load it later.

## Architecture

In modgithub.py we can maintain some globals to track the information we need.
These can be dicts or queues.
They need to be thread safe if accessed from multiple threads concurrently.

```python
# Requests we have not yet responded to: 
request_backlog = {}
# Repos we have cloned / pulled in this run,
# NB! This only tracks the ones we've started, so we don't start them again
#     It does not tell us if they are done pulling or done processing.
pulled_repos = set(string)
# Dictionary of repos we are done cloning and processing (trivy):
repo_results = {}
```

## Starting point

```python

def get_minutes_since_last_abort():
    """Read timestamp from file and compare to now()"""
    pass

def get_new_request_backlog():
    """Read requests from folder, put them in backlog and delete files"""
    pass

def handle_changes():
    """Take all changes requests from backlog, process them and emit responses"""
    pass

def handle_discovery():
    """Take all discovery requests from backlog, process them and emit responses"""
    pass

def handle_processed_repos():
    """Look through backlog for requests matching repos we are done processing, respond to those"""
    pass

def clone_one_repo():
    """Look through backlog for repos we need to clone / process, pick the oldest one download it.
    This function is slow / blocking, but after it is done downloading from github, it starts a background job to do the rest of the processing.
    """
    pass

def main():
    timeout = get_minutes_since_last_abort()
    if timeout <= 60:
        print("Sleeping to avoid unnecessary polling after error / rate limiting")
        sys.exit(0)
    global request_backlog
    get_new_request_backlog() # populates request_backlog global
    while request_backlog:
        # Do easy / fast stuff:
        handle_changes()
        handle_discovery()
        handle_processed_repos()
        # This is the slow part
        clone_one_repo()
        # Do easy / fast stuff:
        handle_changes()
        handle_discovery()
        handle_processed_repos()
        sleep(1)
```

## Limitations / considerations

The current design will block "everything" when cloning one repo is very slow.
In the future we could consider to move even more things (like handle_changes and handle_discovery) to separate threads.

`handle_discovery` is a little bit slow for the first time it runs with an org (to find all repos), this is okay.
