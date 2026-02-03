---
header: 'paintdry - cfgmgmtcamp 2026'
footer: '![image](./Northern-tech-logo-small.png)'
---

<style>
section {
  padding: 50px;
}

header {
    position: absolute;
    left: 50px;
    right: 50px;
    height: 20px;
  top: 10px;
}

footer {
    position: absolute;
    right: 50px;
    left: 1000px;
    height: 20px;
    bottom: 40px;
}

footer > img {
    height: 60px;
}

section > p > img {
    width:  1150px;
}

footer.image_slide {
    display: none;
}

</style>

# Watch paint dry - Monitoring what doesn't change

Ole Herman Schumacher Elgesem, Northern.tech

---

![](./paintdry-robot.svg)

---

## Outline

1. whoami
2. Idea
3. Implementation
4. Examples / demos

---

## whoami

- Ole Herman Schumacher Elgesem
- Northern.tech, the company which makes CFEngine and Mender
- [github.com/olehermanse](https://github.com/olehermanse)

---

## Idea

Started with a few different ideas;

---

## First idea

Website gets compromised - attacker puts malicious JS, or malicious links, or changes one of our downloads (releases of CFEngine, for example).

Website monitoring solutions often focus on other things:
- Defacement and other visual changes
- Performance / response time
- Down detection

---

## Second idea

GitHub / git access gets compromised.
Attacker able to push new commits, tags, releases on GitHub.
Can sneakily add files to existing release, or move tags.

---

## Idea 2.5

Other things are similar - constant, rarely change, or immutable by convention.
Tags on Docker Hub, release artifacts (downloads) on our website, etc.

We don't expect these to change - when they do, it's noteworthy.

---

## paintdry

A database of values which (almost) never change.
Alerting and good tracking of changes.

---

## Risk assessments

- Probable risks
- Impact
- Mitigation effort

- -> Prioritize

---

## Today's goal

- You think this is an interesting idea
- You want to implement something similar in your work
- You want to collaborate on the paintdry implementation

---

## AKA

---

This is not ready, please don't run it in production.

---

## Implementation goals

Configuring it to track the things you want should be easy.

Implementing new modules should be straightforward.

---

## Architecture - modules and configuration

- config.json to indicate what modules you want to use and which resources they should poll
- Python modules to poll the data

---

## Architecture - containers

- PostgreSQL database
- updater:
  - Run modules, put data into database
- downloader:
  - Slow downloads
- pgweb - Open source PG UI
- server / paintdry-gui - Custom react UI & Flask API

---

## A word on rate limiting

---

### Example of a module

Let's quickly look at the DNS module as an example.

---

### Modules - imports

```python
import socket
import time
from functools import cache
from modlib import ModBase, now, normalize_hostname, respond_with_severity
```

---

### Modules - business logic

```python
@cache
def dns_lookup(hostname: str) -> tuple[int, list[str]]:
    time.sleep(1)
    try:
        results = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
        return (now(), sorted([x[4][0] for x in results]))
    except:
        return (now(), [])
```

---

### Modules - Example request

```python
class ModDNS(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "example.com",
                "module": "dns",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "example.com",
                "module": "dns",
                "timestamp": 1730241747,
            },
        ]
```

--- 

### Modules - discovery

- Discover / confirm resource(s).
- Can expand / discover multiple resources, based on one entry from config.
- Module A can "suggest" a new resource from module B.
  - Module B has to confirm it.

---

### Modules - discovery

- Example:
  - DNS module gets resource from config: `example.com`
  - HTTP module gets suggestion from DNS module: `http://example.com`
    - HTTP module can confirm / normalize it: `https://example.com/`
    - HTTP module can also choose to discover more resources:
      - `https://example.com/`
      - `https://example.com/index.html`

--- 

### Modules - discovery

```python
def discovery(self, request: dict) -> list[dict]:
    resource = normalize_hostname(request["resource"])
    timestamp, ips = dns_lookup(resource)
    # DNS module currently does not discover anything extra
    # Just confirm the requested resource:
    return [
        {
            "operation": "discovery",
            "resource": normalize_hostname(resource),
            "module": "dns",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }
    ]
```

---

### Modules - change

Receive a before and after value, assess the "alert" severity:

```python
def change(self, request):
    if request["new_value"] == "":
        return respond_with_severity(request, "high")
    return respond_with_severity(request, "notice")
```

---

### Modules - fin.

~80 lines in total.

```python
def main():
    module = ModDNS()
    module.main()


if __name__ == "__main__":
    main()
```

---

### Modules - summary

1. Business logic
2. Example request
3. Discovery
4. Observation
5. Change

---

## Examples / demos

---

### DNS

- Map hostname to IP address (A record)
  - Alert when this changes

### Git

- Tag -> commit SHA

### GitHub

- Whether a repo is public or private.
- All repos (list)
- Whether a repo is archived
- Security relevant settings (for example rulesets).

---

### Website

- List of external domains linked to
- Number of script tags
- Security relevant HTTP headers (CSP)

---

### Files / downloads

- Stated checksum
- `simplechecksums`
  - Using `sh256sum` `checksums.txt` files
- `cfechecksums`
  - Parses the more custom JSON files we use on cfengine.com

---

## Next steps

- Make the repo public
- Auth (OAuth proxy?), db password, stricter separation
- Better module scheduling
- Better HTTP proxying / caching
  - Could "isolate" secrets to prevent leaking
  - Better implement caching and rate limiting
- Make UI nicer, more useful

---

## Next steps

- Future modules
  - Any ideas?

---

### Future modules

- "Suspicious" git commits
  - Need to define what is suspicious. Could be a combination of:
    - Trusted GPG keys
    - Diffs
    - Email, name, lookalikes?

---

### Future modules

- Actual checksum
- Changes in checksum.txt file
  - New artifact added to existing release?
- Crawl websites recursively
  - Do this recursively for the whole website
  - Find all redirects - alert on changed redirects

---

### Future modules

- Docker tag -> digest
