# Chrono des Vignes
Chrono des Vignes is a timing system for sports events. It allows event organizers to manage events, editions, courses, and runners, and track times and results.

## Features
* Event management: create and manage events, editions, and courses
* Runner management: track runner information and results
* Time tracking: track times and results for each runner
* Multilingual support: supports French, English and German languages

## Getting Started
To get started with Chrono des Vignes, please follow these steps:

1. install (if not already) [uv cli](https://docs.astral.sh/uv/#installation)
1. install npm and node
1. rebuild the venv, .env, db, doc, js, and translation with ```uv run inv init```
1. Launch the server with the following command: ```uv run invoke serve```

### migrate the db (if changed)
```
uv run flask --app chrono_des_vignes db stamp
uv run flask --app chrono_des_vignes db upgrade
```

#### add migration if change the db schema (models.py)
```uv run flask db migrate -m "your migration message"```

 <!--
 not online for now 
## Live Demo
Experience Chrono des Vignes in action by visiting our [Deployed version](https://chronodesvignes.eu.pythonanywhere.com/).

## Documentation
For detailed usage instructions, please refer to our [Documentation](https://chronodesvignes.eu.pythonanywhere.com/doc).
-->
## Contact 
You may contact me at chrono-des-vignes@ikmail.com
or from my github https://github.com/pythonhtmlcssjsarduino/chrono_des_vignes