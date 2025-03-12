# SecDB

A modular system to track security relevant data points over time.
Meant for things you don't expect to change at all, and you'd like a notification when they do.
Examples: Checksums, redirects, certificates, security settings.

Example data:

```SQL
SELECT * FROM resources;
        id |        resource        | module  |   source    |         first_seen         |         last_seen
-----------+------------------------+---------+-------------+----------------------------+----------------------------
         1 | https://cfengine.com/  | http    | config.json | 2024-10-24 13:30:06.018109 | 2024-10-24 13:30:28.72942
         2 | https://mender.io/     | http    | config.json | 2024-10-24 13:30:06.02154  | 2024-10-24 13:30:28.798459
         3 | https://alvaldi.com/   | http    | config.json | 2024-10-24 13:30:06.024935 | 2024-10-24 13:30:28.854112
         4 | https://northern.tech/ | http    | config.json | 2024-10-24 13:30:06.027193 | 2024-10-24 13:30:28.92181
         5 | http://cfengine.com/   | http    | http        | 2024-10-24 13:30:06.211524 | 2024-10-24 13:30:29.094302
         6 | http://mender.io/      | http    | http        | 2024-10-24 13:30:06.41116  | 2024-10-24 13:30:29.270675
         7 | http://alvaldi.com/    | http    | http        | 2024-10-24 13:30:06.567133 | 2024-10-24 13:30:29.408296
         8 | http://northern.tech/  | http    | http        | 2024-10-24 13:30:06.815025 | 2024-10-24 13:30:29.498884
(8 rows)

SELECT * FROM observations;
        id |        resource        | module |     attribute     |         value          |         first_seen         |        last_changed        |         last_seen
-----------+------------------------+--------+-------------------+------------------------+----------------------------+----------------------------+----------------------------
         5 | http://cfengine.com/   | http   | status_code       | 301                    | 2024-10-24 13:30:17.328378 | 2024-10-24 13:30:17.328378 | 2024-10-24 13:30:28.726141
         6 | http://cfengine.com/   | http   | redirect_location | https://cfengine.com/  | 2024-10-24 13:30:17.331634 | 2024-10-24 13:30:17.331634 | 2024-10-24 13:30:28.726189
         7 | http://mender.io/      | http   | status_code       | 301                    | 2024-10-24 13:30:17.394378 | 2024-10-24 13:30:17.394378 | 2024-10-24 13:30:28.795464
         8 | http://mender.io/      | http   | redirect_location | https://mender.io/     | 2024-10-24 13:30:17.396502 | 2024-10-24 13:30:17.396502 | 2024-10-24 13:30:28.79551
         9 | http://alvaldi.com/    | http   | status_code       | 301                    | 2024-10-24 13:30:17.457219 | 2024-10-24 13:30:17.457219 | 2024-10-24 13:30:28.849368
        10 | http://alvaldi.com/    | http   | redirect_location | https://alvaldi.com/   | 2024-10-24 13:30:17.459663 | 2024-10-24 13:30:17.459663 | 2024-10-24 13:30:28.849412
        11 | http://northern.tech/  | http   | status_code       | 301                    | 2024-10-24 13:30:17.509968 | 2024-10-24 13:30:17.509968 | 2024-10-24 13:30:28.918817
        12 | http://northern.tech/  | http   | redirect_location | https://northern.tech/ | 2024-10-24 13:30:17.511439 | 2024-10-24 13:30:17.511439 | 2024-10-24 13:30:28.918903
         1 | https://cfengine.com/  | http   | status_code       | 200                    | 2024-10-24 13:30:06.208006 | 2024-10-24 13:30:06.208006 | 2024-10-24 13:30:29.092379
         2 | https://mender.io/     | http   | status_code       | 200                    | 2024-10-24 13:30:06.408928 | 2024-10-24 13:30:06.408928 | 2024-10-24 13:30:29.268814
         3 | https://alvaldi.com/   | http   | status_code       | 200                    | 2024-10-24 13:30:06.565543 | 2024-10-24 13:30:06.565543 | 2024-10-24 13:30:29.406544
         4 | https://northern.tech/ | http   | status_code       | 200                    | 2024-10-24 13:30:06.812773 | 2024-10-24 13:30:06.812773 | 2024-10-24 13:30:29.496963
(12 rows)
```

## Setup

Manually create `config/secrets.json`:

```
{
  "github_username": "olehermanse",
  "github_access_token": "PUT_GITHUB_PERSONAL_ACCESS_TOKEN_CLASSIC_HERE",
  "github_organizations": ["NorthernTechHQ", "cfengine", "mendersoftware"]
}
```

Also, edit `config/config.json` to avoid using our default config (especially if you don't have access to those repos).

## Run

After editing config and secrets as shown above, run the application with docker-compose:

```
docker compose build && docker compose up
```

Open the UI:

http://127.0.0.1:8000/ui

Or the pgweb UI:

http://127.0.0.1:9000

## Severity

The observations and changes receive a severity level to highlight / rank suspicious values.
Here is a guideline for which level to use:

- `critical` - Urgent issue which is definitely bad and needs immediate attention.
- `high` - Severe issue with real impact and little to no doubt that it's a real issue.
- `medium` - Something which could be bad, but the impact or certainty is limited.
- `low` - Security issues which are not generally exploitable, but could be under certain circumstances.
- `recommendation` - Recommendations which should be fixed, but not directly exploitable.
- `notice` - Notice about a value or change which is noteworthy / doesn't happen often, but needs to be reviewed by a human to understand the impact.
- `unknown` - The module has tried to assess the severity, but it is unknown - likely the module needs to be updated.
- `none` - The value / change is determined to not be an issue at all and should be hidden from views highlighting issues / improvements.
- _Empty string_ - The severity has not been assessed at all, not sent to module yet or no response received back.
