# SecDB

## Idea

Monitor security-relevant information with a focus on what changed and things which might indicate security issues.
Not for monitoring numbers / statistics which change every second, more around things which change on an hourly / daily / weekly basis, for example:

* Web page disappears without redirect
* New script tag appears on a website
* Link to new domain appears on a website
* GitHub Private repo is made public
* Git commit with PGP secret is pushed to public repo
* New search result shows up in Shodan, showing someone who exposed a Mender login page
* New docker image is published
* New release on GitHub

Each of these things should be easy to implement as a _module_ (a python function), and the system should be scalable track hundreds or thousands of these _resources_.

## Components

SecDB consists of a frontend, a backend (API), a database, a configuration file, and an updater.

### Frontend

Currently implemented with HTML / CSS / JS.
Might be updated to React soon.

The frontend uses the backend API to show the database to the user.
Primary functionality includes:

* Searchbar, search for resources and results.
* Single resource view with detailed information and links to other related resources.
* History of recently changed resources, filterable by severity levels.

The frontend is read-only, all updating of the data is done by the updater.

### Updater

Currently implemented as a python script which uses psycopg2 to update the PostgreSQL database

The updater looks at the configuration file and the current state of the database.
It then runs through all the different resources as necessary, updating their data in the database.

### Backend (API)

Currently implemented as a Flask API.

The backend is quite simple: it queries the database for the information needed by the frontend.
Just like the frontend, the backend is read-only, all editing of the database is done in the updater, which does not rely on the backend.

### Database

The database is PostgreSQL running as a separate container in a docker-compose setup.
2 components interact with it directly - the updater and the backend.

## Modules

The database and the configuration file both contain lists of resources.
Each resource is tied to a module (responsible for updating its current state) and has a unique identifier within that module.

## Data / Models

Each resource is modelled as an identifier (typically the URL, a commit SHA, or another type of ID), the current value, the module it belongs to, and some additional metadata.

Let's take a look at a made up example.
We'll make a module for tracking HTTP status code for a URL.
From a security perspective, we might consider 200 normal, but 3xx, 4xx, 5xx could indicate an issue we'd like to be aware of.

**File - config.json**:

```
[
  {
    "module": "http_status",
    "identifier": "https://cfengine.com"
  }
]
```

**Table - config**:

```
     Module,           Identifier, Value
http_status, https://cfengine.com,   200
```

**Output - module**:

```
[
  {
    "module": "http",
    "identifier": "https://cfengine.com",
    "value": "200"
  }
]
```

Thus, the entire responsbility of the module is to receive some instructions about what resources it should watch, and return a list of their current values.

Note that the module returns a list of resources, but this doesn't have to be the same length as the input.
The module might "discover" more resources, for example if it's doing a recursive `wget` download and wants to track each part of a web page as a separate resource.

**Table - resources**:

```
     Module,           Identifier, Value, First seen,  Last seen
http_status, https://cfengine.com,   200, 2023-01-01, 2023-09-31
```

In the table above, the 3 first columns are the most important ones.
**First seen** and **Last seen** are just metadata, more can be added as needed.

## History of changes

The database layer (not the module itself) is responsible for tracking changes in time.
At the most basic level, this means updating the **First seen** and **Last seen** timestamps in the column above.
In addition to this, changes are tracked in a separate table;

**Table - history**:

```
     Module,           Identifier, Value,       Time
http_status, https://cfengine.com,   200, 2023-01-01
http_status, https://cfengine.com,   200, 2023-01-02
http_status, https://cfengine.com,   200, 2023-01-03
http_status, https://cfengine.com,   200, 2023-01-04
http_status, https://cfengine.com,   500, 2023-01-05
http_status, https://cfengine.com,   500, 2023-01-06
http_status, https://cfengine.com,   200, 2023-01-07
http_status, https://cfengine.com,   200, 2023-01-08
http_status, https://cfengine.com,   200, 2023-01-09
http_status, https://cfengine.com,   200, 2023-01-10
http_status, https://cfengine.com,   200, 2023-01-11
http_status, https://cfengine.com,   200, 2023-01-12
http_status, https://cfengine.com,   200, 2023-01-13
http_status, https://cfengine.com,   200, 2023-01-14
```

The example above shows that the website had an internal server error on Jan 5th.
When a website goes from 200 (success) to 500 (internal server error) this information is likely relevant for a security or operations team.
See the section below on alerts.

### Optimization - deduplicate history

As seen above, every time the resource is updated, we create a history entry.
An optimization can be to remove the redundant entries:

```
     Module,           Identifier, Value,       Time
http_status, https://cfengine.com,   200, 2023-01-01
http_status, https://cfengine.com,   200, 2023-01-03
http_status, https://cfengine.com,   500, 2023-01-05
http_status, https://cfengine.com,   500, 2023-01-06
http_status, https://cfengine.com,   200, 2023-01-07
http_status, https://cfengine.com,   200, 2023-01-14
```

In the table above, we've removed all entries where the value was identical both before and after.
Thus, the only information lost is when the information was sampled in those time periods when it was unchanged.
This optimization allows us to eliminate long streaks of identical values, keeping only the data points for when it changed (both before and after the change).
In the example above, we reduced 14 rows to 6 rows, without losing any information we consider significant.

It can also be done on insert; if there is a streak of 2 identical values and you're trying to insert a third one, update the last one instead.

```
     Module,           Identifier, Value,       Time
http_status, https://cfengine.com,   200, 2023-01-07
http_status, https://cfengine.com,   200, 2023-01-10
```

Trying to insert another on `200` on `2023-01-11` would result in:

```
     Module,           Identifier, Value,       Time
http_status, https://cfengine.com,   200, 2023-01-07
http_status, https://cfengine.com,   200, 2023-01-11
```

## Events / alerts

By analyzing the history, we can generate alerts for noteworthy activities.
The approach for creating an alert is to run some code on the before and after state, and consider whether to create an alert or not.
This can be done as a batch or on ever insert to the changes table.
The benefit of using the history table is that you can avoid generating duplicate alerts.
(You generate an alert when the state changes, not ever time you observe the bad state).

### Severity levels

Different levels of alert severity are used:

1. Critical - A severe security issue.
2. Error - Something which is definitely a security issue (or should be treated as it).
3. Warning - Something which seems dangerous, but might not be.
4. Notice - Something which seems more noteworthy than other changes, but is probably not an issue.
5. Information - The default. Most changes in values create events for informational purposes.
   By browsing the timeline filtered at this level you can get a good overview of everything changing in your resources.
6. Verbose - Events which are too noisy (change too often) for information.
   If they were info, they would flood the timeline and make other events harder to see.
7. Debug - Almost equivalent to not generating an event.
   This event is not useful at all to users, only developers / debugging.

### Timeline

In the frontend you can view a timeline of all events (changes) filtered by severity.
Example uses might be:

* Filter for critical and error alerts to respond to real security issues.
* Filter for information to see an overview of everything changing.
* Filter for debug when you are looking into bugs in secdb

### Generating events

A small module (python function) is needed for generating events.
In many cases the default one will be used (generating an information event when value changes).
For the example above, a custom function can be used to generate a critical event when the status code changes to 500.

**Table - events:**

```
     Module,           Identifier, Value,       Time, Old value,   Old time
http_status, https://cfengine.com,   500, 2023-01-05,       200, 2023-01-04
```
