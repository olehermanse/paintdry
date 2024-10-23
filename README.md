# SecDB

A modular system to track security relevant data points over time.
Not for traditional monitoring, more for things you don't expect to change at all, and you'd like a notification when they do.
Examples: Checksums, redirects, certificates, security settings.

Example data:

```SQL
SELECT * FROM config;
 serial_id |        resource        | module |         first_seen         |        last_changed        |         last_seen
-----------+------------------------+--------+----------------------------+----------------------------+----------------------------
         1 | https://cfengine.com/  | http   | 2024-10-24 13:30:06.013239 | 2024-10-24 13:30:06.013239 | 2024-10-24 13:30:28.569186
         2 | https://mender.io/     | http   | 2024-10-24 13:30:06.020857 | 2024-10-24 13:30:06.020857 | 2024-10-24 13:30:28.572474
         3 | https://alvaldi.com/   | http   | 2024-10-24 13:30:06.023032 | 2024-10-24 13:30:06.023032 | 2024-10-24 13:30:28.574294
         4 | https://northern.tech/ | http   | 2024-10-24 13:30:06.026265 | 2024-10-24 13:30:06.026265 | 2024-10-24 13:30:28.576001
(4 rows)

SELECT * FROM resources;
 serial_id |        resource        | modules |   source    |         first_seen         |         last_seen
-----------+------------------------+---------+-------------+----------------------------+----------------------------
         1 | https://cfengine.com/  | {http}  | config.json | 2024-10-24 13:30:06.018109 | 2024-10-24 13:30:28.72942
         2 | https://mender.io/     | {http}  | config.json | 2024-10-24 13:30:06.02154  | 2024-10-24 13:30:28.798459
         3 | https://alvaldi.com/   | {http}  | config.json | 2024-10-24 13:30:06.024935 | 2024-10-24 13:30:28.854112
         4 | https://northern.tech/ | {http}  | config.json | 2024-10-24 13:30:06.027193 | 2024-10-24 13:30:28.92181
         5 | http://cfengine.com/   | {http}  | http        | 2024-10-24 13:30:06.211524 | 2024-10-24 13:30:29.094302
         6 | http://mender.io/      | {http}  | http        | 2024-10-24 13:30:06.41116  | 2024-10-24 13:30:29.270675
         7 | http://alvaldi.com/    | {http}  | http        | 2024-10-24 13:30:06.567133 | 2024-10-24 13:30:29.408296
         8 | http://northern.tech/  | {http}  | http        | 2024-10-24 13:30:06.815025 | 2024-10-24 13:30:29.498884
(8 rows)

SELECT * FROM observations;
 serial_id |        resource        | module |     attribute     |         value          |         first_seen         |        last_changed        |         last_seen
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
