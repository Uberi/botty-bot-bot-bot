#!/usr/bin/env bash

sudo apt-get install -y python3-pip

# modules used by bot
pip3 install slackclient

# modules used by plugins
pip3 install python-dateutil
pip3 install requests
pip3 install recurrent
pip3 install wikipedia
pip3 install sympy
pip3 install pyfiglet
pip3 install google-api-python-client
pip3 install pillow
pip3 install imgurpython
pip3 install pytz

# modules used by web interface
pip3 install flask
pip3 install flask-sqlalchemy
