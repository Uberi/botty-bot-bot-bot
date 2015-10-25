import argparse
from os import path

import httplib2
import oauth2client

flags = argparse.ArgumentParser(parents=[oauth2client.tools.argparser]).parse_args()

# generates `oauth_credentials.json`, which is used by the Botty events plugin in `src/plugins/events/__init__.py`
# make sure to fill in the `"client_id"` and `"client_secret"` fields with the Google Developers API client ID and secret, respectively
# Google Developers API client IDs and secrets can be created by creating a project at https://console.developers.google.com/ and following the instructions under `APIs & auth > Credentials`

APPLICATION_NAME = "Botty McBotterson"
SCOPES = "https://www.googleapis.com/auth/calendar.readonly"
CLIENT_SECRET_FILE = path.join(path.dirname(path.realpath(__file__)), "client_secret.json")
SAVED_OAUTH_CREDENTIALS_FILE = path.join(path.dirname(path.realpath(__file__)), "oauth_credentials.json")

store = oauth2client.file.Storage(SAVED_OAUTH_CREDENTIALS_FILE)
credentials = store.get()
if not credentials or credentials.invalid:
    flow = oauth2client.client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
    flow.user_agent = APPLICATION_NAME
    flow.params["access_type"] = "offline" # ensure we can access the API even when the user is offline
    credentials = oauth2client.tools.run_flow(flow, store, flags)
    print("OAuth credentials successfully set up.")
else:
    print("OAuth credentials already present.")
