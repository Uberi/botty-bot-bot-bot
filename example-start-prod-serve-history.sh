#!/usr/bin/env bash

cd serve-history/
mkdir --parents log
/usr/local/bin/gunicorn server:app --bind 127.0.0.1:8000 --access-logfile log/access.log --error-logfile log/error.log \
    --env "SESSION_SECRET_KEY=SECRET KEY GOES HERE" \
    --env "SLACK_CLIENT_ID=SLACK CLIENT ID GOES HERE" \
    --env "SLACK_CLIENT_SECRET=SLACK CLIENT SECRET GOES HERE" \
    --env "SLACK_AUTHENTICATION_REDIRECT_URL=https://botty.anthonyz.ca/authorize" \
    --env "SLACK_TEAM_ID=SLACK TEAM ID GOES HERE" \
    --env "SLACK_TEAM_DOMAIN=SLACK TEAM DOMAIN GOES HERE"
