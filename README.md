# paintdry - Watch things not change

![](./misc/paintdry-robot.svg)

This project is a security oriented tool for "monitoring" things you don't expect to change.
When they do change, this is somewhwat rare / unexpected, and worthy of some kind of alert.
Other monitoring tools focus on trends and graphs and spikes and outliers, this one focuses on all the security-relevant information we can gather and store, which typically stays constant.
The graphs will be boring, though.

paintdry is implemented in a modular way, to be easily extended with more things to monitor.
The backend uses Python / Flask for the API and PostgreSQL for the database.
2 UIs are provided: pgweb to browse and query tables, as well as a custom UI written in React.

Some examples of things you might want to "monitor" in this way:

- Checksums:
  - Commit SHA associated with a version tag in a git repository.
  - SHA checksum of downloads (installer / binaries).
  - Digest of docker images for specific versions.
- HTTP:
  - You always expect HTTP to redirect to https.
  - Something which is currently status code 200 / 301, you don't expect to change to 404.
  - Security related HTTP headers (like CSP).
- HTML:
  - Number of script tags / domains where javascript is retrieved from.
  - Download links for software.
- GitHub:
  - Whether a repository is public / private.
  - What security settings are enabled or a GitHub repo or organization.
- Git:
  - Number of unsigned commits you've made.
    If you sign all your commits, it should be constant or zero.

All of these are "arguable", depending on how you use git, manage your website, release software, etc. so the goal is to provide configurability to use the tool for things which make sense in your situation.

## Test locally

First, clone the repo:

```sh
git clone https://github.com/olehermanse/paintdry
cd paintdry
```

The repo comes with an example config, after cloning you should be able to run it using `docker compose`:

```sh
docker compose build && docker compose up
```

Custom UI: http://127.0.0.1:9000

PostgreSQL / pgweb: http://127.0.0.1:8000

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
      "command": "python3 /paintdry/modules/moddns.py"
    },
    "http": {
      "command": "python3 /paintdry/modules/modhttp.py"
    },
    "tls": {
      "command": "python3 /paintdry/modules/modtls.py"
    },
    "github": {
      "command": "python3 /paintdry/modules/modgithub.py"
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
