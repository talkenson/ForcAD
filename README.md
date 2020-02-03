[![Build Status](https://travis-ci.org/pomo-mondreganto/ForcAD.svg?branch=master)](https://travis-ci.org/pomo-mondreganto/ForcAD)
[![Rawsec's CyberSecurity Inventory](https://inventory.rawsec.ml/img/badges/Rawsec-inventoried-FF5050_flat.svg)](https://inventory.rawsec.ml/)

# ForcAD

![Front page](static/front_page.png)

Pure-python distributable Attack-Defence CTF platform, created to be easily set up.

The name is pronounced as "forkád".

## Running

5 easy steps to start a game (assuming current working directory to be the project root): 

1. Open `backend/config/config.yml` file 
(or copy `backend/config/config.yml.example` to `backend/config/config.yml`, if the latter is missing).

2. Add teams and tasks to corresponding config sections following the example's format, 
set `start_time` (don't forget your timezone) and `round_time` (in seconds) (for recommendations see 
[checker_timeout](#checkers) variable).

3. Change default passwords (that includes `storages.db.password` for database and `flower.password` for
`celery` visualization).

4. Install `control_requirements.txt` (`pip3 install -r control_requirements.txt`) and run `./control.py setup` 
to transfer config variables

5. Run `docker-compose up --build` to start the system (add `-d` option to detach). 
Wait patiently for the images to build, it could take a few minutes, but happens only once. 

That's all! Now you should be able to access scoreboard at `http://0.0.0.0:8080/`.

###### Before each new game run `./control.py reset` to delete old database and temporary files (and docker networks).

## Configuration and usage

Due to some limitations of docker proxy, teams are identified by unique randomly generated on startup tokens 
(look for them in the logs of `initializer` container or print using the following command after the system started: 
`./control.py print_tokens`). 
You can either share all tokens with all teams (as submitting flags for other teams is not really profitable), 
or send tokens privately. Tokens have one upside: all requests can be masqueraded.

Platform consists of several modules: 

- **TCP flag submitter** (over socat). For each connection send team token in the first line, then flags, each in a new line. 

- **Celerybeat** sends round start events to `celery`

- **Celery** is the main container, which runs checkers. 
Can be scaled using docker command: `docker-compose up --scale celery=n -d` to run `n` instances 
(assuming system is already started). One instance for 10 team-tasks is recommended (so, if there're 8 teams and 6 tasks, 
run 5 instances of `celery`).

- **Flower** is a beautiful celery monitoring app 

- **Redis** acts as a cache, messaging query and backend for celery

- **Postgres** is a persistent game storage

- **Webapi** provides api for react frontend

- **React builder** starts on `docker-compose up`, builds frontend sources and copies them to the volume 
from which they're served by nginx

- **Nginx** acts as a routing proxy, that unites frontend, api and flower

- **Initializer** also starts on `docker-compose up`, waits for the database to start (all other containers wait for 
the initializer to finish its job) then drops old tables and initializes database. From that point,
changing team or task config is useless, as they're copied to database already. If changes are required, connect to 
the postgres container directly and run `psql` command (read the reference). For default database name and user 
(`system_db` and `system_admin`) use `docker-compose exec postgres psql -U system_admin system_db` (no password 
is required as it's a local connection). 

Platform has a somewhat-flexible rating system. Basically, rating system is a class that's initialized by 2 floats: 
current attacker and victim scores and has `calculate` method that returns another 2 floats, attacker and 
victim rating changes respectively. Having read that, you can easily replace default rating system in 
[C rating system](backend/rs_implementation/rating_system.c) by your own brand-new one. Default rating system is based on Elo 
rating and performs quite well in practice. **game_hardness** and **inflation** configuration variables can be set in `global` 
block in `config.yml`, the first one sets how much points team is earning for an attack (the higher the hardness, the 
bigger the rating change is), and the second one states is there's an "inflation" of points: whether a team earns points
by attacking zero-rating victim. Current rating system with inflation results in quite a dynamic and fast gameplay.
Default value for `game_hardness` in both versions (with and w/o inflation) is `1300`, recommended range is 
`[500, 10000]` (try to emulate it first). Initial score for task can also be configured in global settings (that'll be
the default value) and for each task independently.

System uses the most common flag format by default: `[A-Z0-9]{31}=`, the first symbol is the first letter of 
corresponding service name. You can change flag generation in function `generate_flag` in 
[backend/helpers/flags.py](backend/helplib/flags.py)

Each flag is valid (and can be checked by checker) for `flag_lifetime` rounds (global config variable).    

## Checkers

Checksystem is completely compatible with Hackerdom checkers, but some config-level enhancements were added (see below).
Checkers are configured for each task independently. It's recommended to put each checker in a separate folder 
under `checkers` on project root. Checker is considered to consist of the main executable and some 
auxiliary files in the same folder.

Checker-related configuration variables: 

- `checker`: path to the main checker executable (relative to `checkers` folder)

- `gets`: number of flags to put for each team for each round

- `puts`: number of flags to check from the last `flag_lifetime` rounds 
(see [Configuration and usage](#configuration-and-usage) for lifetime description). 

- `places`: large tasks may contain a lot of possible places for a flag, that is the number. 
It'll be passed to checker (the range is `[1, places]`).

- `checker_timeout` (seconds): timeout for **each** checker action. As there're 3 actions run in a row, with some latency 
between them, I recommend setting `round_time` at least 4 times greater than the maximum checker timeout. 

- `checker_returns_flag_id`: whether the checker returns new `flag_id` for the `GET` action for this flag, or the 
passed `flag_id` should be used when getting flag (see more in [checker writing](#writing-a-checker) section)

- `env_path`: path or a combination of paths to be prepended to `PATH` env variable (e.g. path to chromedriver). 
By default, `checkers/bin` is used, so all auxiliary executables can be but there. 

## Writing a checker

Checker is an app that checks whether the team's task is running normally, puts flags and then checks them after a few rounds. 

Actions and arguments are passed to checker as command-line arguments, first one is always command type, second is team host.

Checker should terminate with one of the five return codes: 

- **101**: `OK` code, everything works
- **102**: `CORRUPT`, service's working correctly, but didn't return flags from previous rounds (returned by `GET` only)
- **103**: `MUMBLE`, service's not working correctly
- **104**: `DOWN`, could not connect normally
- **110**: `CHECKER_ERROR`, unexpected error in checker

All other return codes are considered to be `CHECKER_ERROR`.

In case of unsuccessful invocation `stdout` output will be shown on scoreboard, `stderr` output is considered to 
be the debug info and is stored in database. Also, in case of `CHECKER_ERROR` `celery` container prints warning 
to console with detailed logs. 

Checker must implement three main actions: 

--------

- `CHECK`: checks that team's service is running normally. Visits some pages, checks registration, login, etc...

Example invocation: `/checkers/task/check.py check 127.0.0.1`

-----

- `PUT`: puts a flag to the team's service.

Example invocation: `/checkers/task/check.py put 127.0.0.1 <flag_id> <flag> <vuln_number>`

If the checker returns `flag_id` (see [checker config](#checkers)), it should write some data 
which helps to access flag later (username, password, etc) to `stdout`. Otherwise, it ought to use `flag_id` as some "seed" 
to generate such data (on the next invocation `flag_id` will be the same if `checker_returns_flag_id` is set to `false`).

`PUT` is **not** run if `CHECK` failed

------

- `GET`: fetches one random old flag from last `flag_lifetime` rounds. 

Example invocation: `/checkers/task/check.py get 127.0.0.1 <flag_id> <flag> <vuln_number>`

This action should check if the flag can be acquired correctly.

`GET` is **not** run if `CHECK` or `PUT` fail. 

------

Be aware that to test task locally, LAN IP (not `127.0.0.1`) needs to be specified for the team.

See [this link](https://github.com/HackerDom/ructf-2017/wiki/Интерфейс-«проверяющая-система-чекеры») to read more about 
writing checkers for Hackerdom checksystem. Vulns' frequencies (e.g. put 1 flag for the first vuln for each 
3 flags of the second) are not supported yet, but can be easily emulated with task place count and checker. 
For example, for the above configuration (1:3) specify 4 places for the task, and then in checker `PUT` flag for the 
first vuln if the supplied place is 1 and to the second vuln otherwise.    

#### Modifying checker container

As checkers run in `celery` container, open [docker_config/celery/Dockerfile](docker_config/celery/Dockerfile) 
and install all necessary packages to the image. Any modification can be made in `CUSTOMIZE` block. 
With enough confidence, even the base image of celery container could be changed 
(`python3.7` needs to be installed anyway).

## Running without docker 

Starting system without docker  is quite easy too: just run all the needed parts of the system 
(see [Configuration and usage](#configuration-and-usage) section for details) and provide correct values 
for `redis` and `postgres` machine hosts.

Python version `3.7` (and higher) is required (may work with `3.6.7+`, but it hasn't been tested at all).
