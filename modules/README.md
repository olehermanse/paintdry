# Writing modules for paintdry

Modules in paintdry are Python scripts that extend the `ModBase` class from `modlib.py`.
Each module handles specific types of resources (DNS lookups, HTTP checks, TLS certificates, etc.).

## Module Structure

A minimal module looks like this:

```python
from modlib import ModBase

class ModMyModule(ModBase):
    def example_requests(self):
        return [
            {
                "operation": "discovery",
                "resource": "example.com",
                "module": "mymodule",
                "source": "config.json",
                "timestamp": 1730241747,
            },
            {
                "operation": "observation",
                "resource": "example.com",
                "module": "mymodule",
                "timestamp": 1730241747,
            },
        ]

    def discovery(self, request: dict) -> list[dict]:
        # Return discovered resources
        return []

    def observation(self, request: dict) -> list[dict]:
        # Return observations about a resource
        return []

    def change(self, request: dict) -> list[dict]:
        # Handle changes (old_value -> new_value)
        return []

def main():
    module = ModMyModule()
    module.main()

if __name__ == "__main__":
    main()
```

## Request Format

Requests are JSON dictionaries with these required fields:

| Field       | Type   | Description                                        |
| ----------- | ------ | -------------------------------------------------- |
| `operation` | string | One of: `discovery`, `observation`, `change`       |
| `resource`  | string | The resource being monitored (hostname, URL, etc.) |
| `module`    | string | The module name                                    |
| `timestamp` | int    | Unix timestamp                                     |

Additional fields for specific operations:

- **discovery**: `source` - where the request originated (e.g., "config.json")
- **change**: `old_value`, `new_value` - the before and after value for the change

## Operations

### discovery

Called to discover resources.
Returns a list of discovery results confirming/expanding resources.

```python
def discovery(self, request: dict) -> list[dict]:
    return [
        {
            "operation": "discovery",
            "resource": request["resource"],
            "module": "mymodule",
            "source": request["source"],
            "timestamp": request["timestamp"],
        }
    ]
```

### observation

Called to observe/check a resource.
Returns observations with attributes and severity.

```python
def observation(self, request: dict) -> list[dict]:
    return [
        {
            "operation": request["operation"],
            "resource": request["resource"],
            "module": "mymodule",
            "attribute": "some_attribute",
            "value": "observed_value",
            "timestamp": now(),
            "severity": "none",  # none, notice, high, unknown
        }
    ]
```

### change

Called when a value changes.
Use `respond_with_severity()` helper to set severity.

```python
from modlib import respond_with_severity

def change(self, request):
    if request["new_value"] == "":
        return respond_with_severity(request, "high")
    return respond_with_severity(request, "notice")
```

## Severity Levels

- `critical` - Urgent issue which is definitely bad and needs immediate attention.
- `high` - Severe issue with real impact and little to no doubt that it's a real issue.
- `medium` - Something which could be bad, but the impact or certainty is limited.
- `low` - Security issues which are not generally exploitable, but could be under certain circumstances.
- `recommendation` - Recommendations which should be fixed, but not directly exploitable.
- `notice` - Notice about a value or change which is noteworthy / doesn't happen often, but needs to be reviewed by a human to understand the impact.
- `unknown` - The module has tried to assess the severity, but it is unknown - likely the module needs to be updated.
- `none` - The value / change is determined to not be an issue at all and should be hidden from views highlighting issues / improvements.
- _Empty string_ - The severity has not been assessed at all, not sent to module yet or no response received back.


## Helper Functions

Import from `modlib`:

- `now()` - Returns current Unix timestamp
- `normalize_hostname(hostname)` - Strips `www.` prefix and extracts hostname from URLs
- `normalize_url(url)` - Ensures URL has `https://` prefix and trailing slash
- `respond_with_severity(request, severity)` - Helper for change responses

## Running Modules

Modules can be run in three modes:

1. **Example mode**: `python moddns.py example` - Runs example requests for testing
2. **File mode**: `python moddns.py <input_dir> <output_dir> <cache_dir>` - Processes JSON files
3. **Stdin mode**: Reads JSON requests from stdin, writes responses to stdout

## File Naming Convention

Module files should be named `mod<name>.py` (e.g., `moddns.py`, `modhttp.py`).
