#!/usr/bin/env bash

sudo apt-get install python3-pip

# we have to install from the GitHub repo for now since the PyPI version is Python 2 only
#sudo pip3 install slackclient
sudo pip3 install git+git://github.com/slackhq/python-slackclient.git

# modules used by plugins
sudo apt-get install python3-dateutil
sudo pip3 install requests
sudo pip3 install recurrent
sudo pip3 install wikipedia
sudo pip3 install sympy
sudo pip3 install pyfiglet
sudo pip3 install google-api-python-client
sudo apt-get install python3-pillow
sudo pip3 install imgurpython

# modules used by web interface
sudo pip3 install flask
sudo pip3 install flask-sqlalchemy
