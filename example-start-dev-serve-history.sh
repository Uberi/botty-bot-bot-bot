#!/usr/bin/env bash

export SESSION_SECRET_KEY="SECRET KEY GOES HERE" # should be a long random secret string
export SLACK_CLIENT_ID="SLACK CLIENT ID GOES HERE" # get this from your Slack App's page under https://api.slack.com/apps
export SLACK_CLIENT_SECRET="SLACK CLIENT SECRET GOES HERE" # get this from your Slack App's page under https://api.slack.com/apps
export SLACK_AUTHORIZATION_REDIRECT_URL="http://localhost:5000/authorize" # should be of the form "(CURRENT SERVER'S HOST)/authorize", and must be publicly accessible from the internet
export SLACK_TEAM_ID="SLACK TEAM ID GOES HERE" # get this from https://api.slack.com/methods/team.info/test
export SLACK_TEAM_DOMAIN="SLACK TEAM DOMAIN GOES HERE" # get this from https://api.slack.com/methods/team.info/test

python3 serve-history/server.py
