# SecDB

## Test locally

The repo comes with an example config, after cloning you should be able to run it using `docker compose`:

```sh
docker compose build && docker compose up
```

Custom UI: http://127.0.0.1:9000

PostgreSQL / pgweb: http://127.0.0.1:8000

## Rationale

A modular system to track security relevant data points over time, focusing on values you don't expect to change.

Some examples:

- Checksums of released software
- Redirects for HTTP to HTTPS, security.txt files, etc.
- SSL certificates
- Security settings in GitHub

When these things significantly change, it'd probably be nice to receive an alert.
Given the premise of only focusing on data which is _expected to be static_, it is easier to make a system with fewer false positives.
Other security monitoring systems usually focus on things like:

- Numbers which change over time (uptime, requests per second, load average)
- Log messages
- Visual changes to websites and defacement attacks
- Uptime monitoring ("Is the website down?")
- Broken / 404 links

While examining and tracking those things makes sense and is valuable, there is an inherent problem of noise and false positives.
You have to look at patterns, and try to determine what is normal, and what is the threshold for something abnormal.

However, it is valuable to turn the problem on its head, and ask the question:

> What are the things we never expect to change?

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

## Database

Example data:

```
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

## Configuration

By default, the repo will work with some example configuration (as can be seen in `config/config.json`).

You can override it with your own configuration;

```bash
cp config/config.json config/config-override.json
```

Start editing `config-override.json` to your liking.
It could for example look like this, if you're interested in monitoring Northern.tech resources:

```json
{
  "targets": [
    {
      "modules": ["http", "dns", "tls"],
      "resources": [
        "https://northern.tech",
        "https://cfengine.com",
        "https://mender.io"
      ]
    },
    {
      "modules": ["github"],
      "resources": ["NorthernTechHQ", "mendersoftware", "cfengine"]
    }
  ],
  "modules": {
    "dns": {
      "command": "python3 /secdb/modules/moddns.py"
    },
    "http": {
      "command": "python3 /secdb/modules/modhttp.py"
    },
    "tls": {
      "command": "python3 /secdb/modules/modtls.py"
    },
    "github": {
      "command": "python3 /secdb/modules/modgithub.py",
      "slow": true
    }
  }
}
```

If you're using modules which need secrets, such as the `github` module, you will need to create the `config/secrets.json`:

```json
{
  "github_username": "olehermanse",
  "github_access_token": "PUT_GITHUB_PERSONAL_ACCESS_TOKEN_CLASSIC_HERE",
  "github_organizations": ["NorthernTechHQ", "cfengine", "mendersoftware"]
}
```

## Run

After editing config and secrets as shown above, run the application with docker-compose:

```
docker compose build && docker compose up
```

Open the UI:

http://127.0.0.1:8000

Or the pgweb UI:

http://127.0.0.1:9000

## License

Copyright (C) 2025 Ole Herman Schumacher Elgesem

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
