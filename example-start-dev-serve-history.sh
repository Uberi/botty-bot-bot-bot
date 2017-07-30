#!/usr/bin/env bash

export SESSION_SECRET_KEY="SECRET KEY GOES HERE"
export SLACK_CLIENT_ID="SLACK CLIENT ID GOES HERE"
export SLACK_CLIENT_SECRET="SLACK CLIENT SECRET GOES HERE"
export SLACK_AUTHENTICATION_REDIRECT_URL="http://localhost:5000/authenticate" # this needs to be a publicly accessible endpoint
export SLACK_TEAM_ID="SLACK TEAM ID GOES HERE" # get this from https://api.slack.com/methods/team.info/test

python3 serve-history/server.py
