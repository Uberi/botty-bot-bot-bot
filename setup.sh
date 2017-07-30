#!/usr/bin/env bash

# modules used by bot
python3 -m pip install --upgrade slackclient

# modules used by plugins
python3 -m pip install --upgrade python-dateutil
python3 -m pip install --upgrade requests
python3 -m pip install --upgrade recurrent
python3 -m pip install --upgrade wikipedia
python3 -m pip install --upgrade sympy
python3 -m pip install --upgrade pyfiglet
python3 -m pip install --upgrade google-api-python-client
python3 -m pip install --upgrade pillow
python3 -m pip install --upgrade imgurpython
python3 -m pip install --upgrade pytz

# modules used by history UI
python3 -m pip install --upgrade wheel
python3 -m pip install --upgrade requests
python3 -m pip install --upgrade slackclient
python3 -m pip install --upgrade flask
python3 -m pip install --upgrade flask-sqlalchemy
python3 -m pip install --upgrade flask-caching
python3 -m pip install --upgrade cachetools
python3 -m pip install --upgrade gunicorn