"""
Implements OAuth2 authorization with Slack.

### Recommended workflow with Flask

Add the `/login` and `/logout` endpoints to your Flask app:

```python
@app.route("/login")
def login():
    return slack_auth.login(SLACK_TEAM_ID, SLACK_CLIENT_ID, SLACK_AUTHORIZATION_REDIRECT_URL)
@app.route("/logout", methods=["POST"])
def logout():
    return slack_auth.logout("/")
```

Add callback endpoint for the Slack API will return authorization results to (the endpoint must also be specified in the Slack App settings):

```python
@app.route("/authorize")
def authorize():
    after_login_url = slack_auth.get_after_login_url() or "/"
    return slack_auth.authorize(SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, after_login_url, flask.redirect(after_login_url))
```

Add a decorator to conveniently protect endpoints using Slack login.

```python
slack_membership_required = slack_auth.team_membership_required(
    SLACK_TEAM_ID,
    lambda page_url: flask.url_for("login", next=page_url)
)
```

Use the decorator in endpoints:

```python
@app.route("/")
@slack_membership_required
def hello():
    return "Hello World!"
```

Now, whenever you try to access the top-level page of the app, you'll be asked to login with Slack, and then redirected to the original page afterward.
"""

import json
import uuid
from functools import wraps
from urllib.parse import urlencode
import time

import flask
import requests

# maximum number of seconds before another users.identity Slack API call is required to re-validate a previously validated token
# we don't call users.identity on every request because that would really slow things down, so we simply make sure we've called it recently enough that we feel safe trusting that it's still validated
AUTHORIZATION_TIMEOUT = 60 * 10

# whether to disable authorization when the app is in debug mode
DISABLE_AUTHORIZATION_IN_DEBUG_MODE = True

def login(slack_team_id, slack_client_id, slack_oauth_redirect_url):
    """
    Redirects to the OAuth2 authorization page for the Slack team specified by `slack_team_id`, using the client ID `slack_client_id` and redirecting to `slack_oauth_redirect_url` afterward.

    `slack_team_id` can be found by going to the [team.info API tester](https://api.slack.com/methods/team.info/test) and taking the value of the "id" field under "team" in the result.

    `slack_client_id` and `slack_oauth_redirect_url` can be found in your [Slack app configuration](https://api.slack.com/apps).
    """
    params = {
        "client_id": slack_client_id,
        "scope": "identity.basic",
        "redirect_url": slack_oauth_redirect_url,
        "team": slack_team_id,
    }
    if "next" in flask.request.args:
        params["state"] = flask.request.args["next"]
    return flask.redirect("https://slack.com/oauth/authorize?" + urlencode(params))

def logout(next_page_url):
    if "slack_auth_api_token" in flask.session:
        requests.get("https://slack.com/api/auth.revoke", params={"token": flask.session["slack_auth_api_token"]})
        del flask.session["slack_auth_api_token"]
    if "slack_auth_user_id" in flask.session:
        del flask.session["slack_auth_user_id"]
    if "slack_auth_team_id" in flask.session:
        del flask.session["slack_auth_team_id"]
    return flask.redirect(next_page_url)

def get_after_login_url():
    return flask.request.args.get("state")

def authorize(slack_client_id, slack_client_secret, next_page_url, authorization_failure_page):
    # handle user declining the authorization request
    if flask.request.args.get("error"):
        return authorization_failure_page

    # exchange the OAuth authorization code for a Slack API token
    oauth_authorization_code = flask.request.args.get("code")
    if oauth_authorization_code is None:
        return authorization_failure_page
    slack_access_result = requests.get("https://slack.com/api/oauth.access", params={
        "client_id": slack_client_id,
        "client_secret": slack_client_secret,
        "code": oauth_authorization_code,
    }).json()
    if not slack_access_result["ok"]:
        return authorization_failure_page
    slack_api_token = slack_access_result.get("access_token")

    # confirm the user identity to get the username
    slack_authorization_result = requests.get("https://slack.com/api/users.identity", params={"token": slack_api_token}).json()
    if not slack_authorization_result.get("ok"):
        return authorization_failure_page
    authorized_user_id, authorized_team_id = slack_authorization_result["user"]["id"], slack_authorization_result["team"]["id"]

    # mark the user as logged in
    flask.session["slack_auth_time"] = time.time()
    flask.session["slack_auth_api_token"] = slack_api_token
    flask.session["slack_auth_user_id"] = authorized_user_id
    flask.session["slack_auth_team_id"] = authorized_team_id

    # redirect to the URL we wanted to visit before
    return flask.redirect(next_page_url)

def team_membership_required(slack_team_id, get_authorization_failure_page):
    """
    Decorator factory for Flask endpoints for ensuring that the user is a member of the Slack team specified by `slack_team_id`.
    """
    def team_membership_required_decorator(route_function):
        @wraps(route_function)
        def team_membership_required_decorator_wrapper(*args, **kwargs):
            # don't require logging in if DISABLE_AUTHORIZATION_IN_DEBUG_MODE is set and we're in debug mode
            if DISABLE_AUTHORIZATION_IN_DEBUG_MODE and flask.current_app.debug:
                return route_function(*args, **kwargs)

            # check if user has been authorized for the required team
            if flask.session.get("slack_auth_team_id") != slack_team_id:
                return get_authorization_failure_page(flask.request.url)

            # check if the user's authorization has been validated recently enough
            current_time = time.time()
            if not (current_time - AUTHORIZATION_TIMEOUT <= flask.session.get("slack_auth_time", float("-inf")) <= current_time):
                # retrieve token authorization metadata
                slack_api_token = flask.session.get("slack_auth_api_token")
                slack_authorization_result = requests.get("https://slack.com/api/users.identity", params={"token": slack_api_token}).json()
                if not slack_authorization_result["ok"]:
                    return get_authorization_failure_page(flask.request.url)
                authorized_user_id, authorized_team_id = slack_authorization_result["user"]["id"], slack_authorization_result["team"]["id"]

                # check if user has been authorized for the required team
                if authorized_team_id != slack_team_id:
                    return get_authorization_failure_page(flask.request.url)

                # refresh the authorization to make sure it's fresh for next time
                flask.session["slack_auth_time"] = time.time()
                flask.session["slack_auth_api_token"] = slack_api_token
                flask.session["slack_auth_user_id"] = authorized_user_id
                flask.session["slack_auth_team_id"] = authorized_team_id

            # run the original route
            return route_function(*args, **kwargs)
        return team_membership_required_decorator_wrapper

    return team_membership_required_decorator