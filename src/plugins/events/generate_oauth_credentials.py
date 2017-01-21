#!/usr/bin/env python3

import argparse
from os import path

import httplib2
from oauth2client.file import Storage
from oauth2client.client import flow_from_clientsecrets
from oauth2client import tools

print("""This script takes a Google OAuth Client file `client_secret.json`, and uses it to generate an OAuth Credentials file `oauth_credentials.json`, which is used by the Botty events plugin in `src/plugins/events/__init__.py`.

To use this script:

1. Go to https://console.developers.google.com/apis/credentials and create a new OAuth Client ID named "Botty", selecting "Other" for the application type.
2. Download the OAuth Client file from that page - it's named something like `client_secret_SOMETHING.apps.googleusercontent.com.json`.
3. Save the file to `client_secret.json` in this directory, overwriting the current `client_secret.json`.
4. Run this script. It should open a web browser to an OAuth authorization flow, where you can allow read-only access to calendars, after which `oauth_credentials.json` is updated to contain the OAuth credentials.
5. The Botty events plugin should now be able to read its configured calendars.
""")

INPUT_CLIENT_SECRET_FILE = path.join(path.dirname(path.realpath(__file__)), "client_secret.json")
OUTPUT_OAUTH_CREDENTIALS_FILE = path.join(path.dirname(path.realpath(__file__)), "oauth_credentials.json")
APPLICATION_NAME = "Botty McBotterson"
SCOPES = "https://www.googleapis.com/auth/calendar.readonly"

flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()

store = Storage(OUTPUT_OAUTH_CREDENTIALS_FILE)
credentials = store.get()
if not credentials or credentials.invalid:
    flow = flow_from_clientsecrets(INPUT_CLIENT_SECRET_FILE, SCOPES)
    flow.user_agent = APPLICATION_NAME
    flow.params["access_type"] = "offline" # ensure we can access the API even when the user is offline
    credentials = tools.run_flow(flow, store, flags)
    print("OAuth credentials successfully set up.")
else:
    print("OAuth credentials already present and valid.")
