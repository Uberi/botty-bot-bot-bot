#!/usr/bin/env python3

import os
import re
import json, uuid
import html
from functools import wraps
from urllib.request import urlopen
from urllib.parse import urlencode
from datetime import datetime

import flask
from flask import jsonify
from flask_caching import Cache

import slack_auth
import models
from models import Channel, User, get_messages

SCRIPT_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

DATABASE_URL = "sqlite:///{}".format(os.path.join(SCRIPT_DIRECTORY, "history.db"))

# settings for serving files
FILES_DIRECTORY = os.path.join(SCRIPT_DIRECTORY, "..", "@history", "files")
FILES_REWRITE_PATH = "/_static_internal/{filename}"

# settings for slack authentication
SESSION_SECRET_KEY = os.environ["SESSION_SECRET_KEY"]
SLACK_CLIENT_ID = os.environ["SLACK_CLIENT_ID"]
SLACK_CLIENT_SECRET = os.environ["SLACK_CLIENT_SECRET"]
SLACK_AUTHENTICATION_REDIRECT_URL = os.environ["SLACK_AUTHENTICATION_REDIRECT_URL"]
SLACK_TEAM_ID = os.environ["SLACK_TEAM_ID"]
SLACK_TEAM_DOMAIN = os.environ["SLACK_TEAM_DOMAIN"]

PAGE_SIZE = 5000

# set up application
app = flask.Flask(__name__)
app.secret_key = SESSION_SECRET_KEY # used to encrypt flask.session cookies on the client side
DEBUG_MODE = False # set to True when running using local Flask server

# set up caching
cache = Cache(app, config={"CACHE_TYPE": "simple"})

# set up database
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
models.initialize_db(app)

# set up login using Slack OAuth
@app.route("/login")
def login():
    return slack_auth.login(SLACK_TEAM_ID, SLACK_CLIENT_ID, SLACK_AUTHENTICATION_REDIRECT_URL)
@app.route("/logout", methods=["POST"])
def logout():
    return slack_auth.logout("/")
@app.route("/authenticate")
def authenticate():
    after_login_url = slack_auth.get_after_login_url() or "/"
    return slack_auth.authenticate(SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, after_login_url, flask.redirect(after_login_url))
slackegginess_required = slack_auth.team_membership_required(
    SLACK_TEAM_ID,
    lambda page_url: flask.render_template("login.html", login_url=flask.url_for("login", next=page_url))
)

def retrieve_requested_messages(request_args):
    param_from, param_to = request_args.get("from"), request_args.get("to")
    param_channel_ids, param_user_ids = request_args.get("channel_ids"), request_args.get("user_ids")
    param_text = request_args.get("text")
    param_sort = request_args.get("sort")
    param_offset = request_args.get("offset")

    # validate parameters
    filter_from, filter_to = None, None
    filter_channel_ids, filter_user_ids = None, None
    filter_text = None
    result_sort = "time-ascending"
    result_offset = 0
    if param_from is not None:
        try: filter_from = int(param_from)
        except ValueError:
            response = jsonify({"message": "Invalid `from` parameter \"{}\" - must be valid UNIX timestamp".format(param_from)})
            response.status_code = 400
            return response, None, None
    if param_to is not None:
        try: filter_to = int(param_to)
        except ValueError:
            response = jsonify({"message": "Invalid `to` parameter \"{}\" - must be valid UNIX timestamp".format(param_to)})
            response.status_code = 400
            return response, None, None
    if param_channel_ids is not None:
        filter_channel_ids = set()
        for param_channel_id in param_channel_ids.split(","):
            if Channel.query.filter_by(channel_id=param_channel_id).first() is None:
                response = jsonify({"message": "Invalid Slack channel ID \"{}\" in `channel_ids` parameter - must be valid Slack channel ID".format(param_channel_id)})
                response.status_code = 400
                return response, None, None
            filter_channel_ids.add(param_channel_id)
        filter_channel_ids = frozenset(filter_channel_ids)
    if param_user_ids is not None:
        filter_user_ids = set()
        for param_user_id in param_user_ids.split(","):
            if User.query.filter_by(user_id=param_user_id).first() is None:
                response = jsonify({"message": "Invalid Slack user ID \"{}\" in `user_ids` parameter - must be valid Slack user ID".format(param_user_id)})
                response.status_code = 400
                return response, None, None
            filter_user_ids.add(param_user_id)
        filter_user_ids = frozenset(filter_user_ids)
    if param_text is not None:
        try: re.compile(param_text)
        except ValueError:
            response = jsonify({"message": "Invalid `text` parameter \"{}\" - must be valid Python-style regular expression".format(param_text)})
            response.status_code = 400
            return response, None, None
    if param_sort is not None:
        if param_sort not in {"time-ascending", "time-descending", "channel-ascending", "channel-descending", "user-ascending", "user-descending"}:
            response = jsonify({"message": "Invalid `sort` parameter \"{}\" - must be one of \"time-ascending\", \"time-descending\", \"channel-ascending\", \"channel-descending\", \"user-ascending\", or \"user-descending\"".format(param_sort)})
            response.status_code = 400
            return response, None, None
        result_sort = param_sort
    if param_offset is not None:
        try:
            result_offset = int(param_offset)
            if result_offset < 0: raise ValueError("`offset` must be non-negative")
        except ValueError:
            response = jsonify({"message": "Invalid `offset` parameter \"{}\" - must be valid non-negative integer".format(param_offset)})
            response.status_code = 400
            return response, None, None

    messages, message_count = get_messages(filter_from, filter_to, filter_channel_ids, filter_user_ids, filter_text, result_sort, result_offset, PAGE_SIZE)
    return None, messages, message_count

@app.template_filter("set_request_arg")
def set_request_arg(request_args, arg_name, arg_value=None):
    new_args = request_args.copy()
    if arg_value is None:
        if arg_name in new_args:
            del new_args[arg_name]
    else:
        new_args[arg_name] = arg_value
    return new_args
@app.template_filter("url_from_request_args")
def url_from_request_args(request_args):
    return flask.request.path + "?" + urlencode(request_args)

@app.template_filter("html_from_slack_sendable_text")
def html_from_slack_sendable_text(message):
    channel_id, user_id, sendable_text = message.channel_id, message.user_id, message.value
    request_args = flask.request.args.to_dict()

    def process_special_sequence(match):
        original, body = match.group(0), match.group(1).split("|")[0]
        if body.startswith("#"):  # channel reference
            new_url = url_from_request_args(set_request_arg(request_args, "channel_ids", body[1:]))
            channel = Channel.query.filter_by(channel_id=body[1:]).first()
            channel_name = "[DELETED]" if channel is None else channel.channel_name  # apparently channels can be truly deleted, rather than just archived
            return """<a href="{new_url}">#{channel_name}</a>""".format(
                new_url=html.escape(new_url), channel_name=html.escape(channel_name)
            )
        if body.startswith("@"):  # user reference
            new_url = url_from_request_args(set_request_arg(request_args, "user_ids", body[1:]))
            user = User.query.filter_by(user_id=body[1:]).first()
            return """<a href="{new_url}" title="{user_real_name}">@{user_name}</a>""".format(
                new_url=html.escape(new_url), user_name=html.escape(user.user_name), user_real_name=html.escape(user.user_real_name)
            )
        if body in {"!channel", "!group"}:
            return """<strong>@channel</strong>"""
        if body == "!everyone":
            return """<strong>@everyone</strong>"""
        return original

    def process_slack_file_link(match):
        original, channel_id, file_slack_name = match.group(0), match.group(1), match.group(2)
        archived_url = "/uploaded_files/{}-{}".format(channel_id, file_slack_name)
        return """<a href="{}">{}</a>""".format(archived_url, original)

    # process Slack special sequences
    html_text = re.sub(r"<(.*?)>", process_special_sequence, sendable_text)

    # process Slack file links
    html_text = re.sub(r"\bhttps://{}\.slack\.com/files/[^/]+/(\w+)/([^/\s]+)".format(SLACK_TEAM_DOMAIN), process_slack_file_link, html_text)

    return html_text

@app.route("/uploaded_files/<path:filename>")
@slackegginess_required
def uploaded_file(filename):
    # don't assume Nginx is in place if we're in debug mode - just send the file directly
    if app.debug:
        return flask.send_from_directory(FILES_DIRECTORY, filename)

    # tell Nginx to serve the file using the special "X-Accel-Redirect" header (way more efficient than using Flask to serve it)
    response = flask.make_response("")  # empty response
    del response.headers["Content-Type"]  # remove Content-Type header - allows Nginx to auto-detect the MIME type using the file extension
    response.headers["X-Accel-Redirect"] = FILES_REWRITE_PATH.format(filename=filename)  # make an internal redirect to the actual file
    return response

@app.route("/")
@slackegginess_required
@cache.cached(timeout=60 * 10, query_string=True)
def index():
    channels, users = Channel.query.all(), User.query.all()
    error_response, messages, message_count = retrieve_requested_messages(flask.request.args)
    if error_response is not None: return error_response

    request_args = flask.request.args.to_dict()
    offset = int(request_args.get("offset", "0"))
    has_previous_page, has_next_page = offset >= PAGE_SIZE, offset + PAGE_SIZE < message_count

    first_page_url = url_from_request_args(set_request_arg(request_args, "offset", 0)) if has_previous_page else None
    previous_page_url = url_from_request_args(set_request_arg(request_args, "offset", offset - PAGE_SIZE)) if has_previous_page else None
    next_page_url = url_from_request_args(set_request_arg(request_args, "offset", offset + PAGE_SIZE)) if has_next_page else None
    last_page_url = url_from_request_args(set_request_arg(request_args, "offset", ((message_count - 1) // PAGE_SIZE) * PAGE_SIZE)) if has_next_page else None

    filter_from = datetime.fromtimestamp(int(request_args["from"])) if "from" in request_args else None
    filter_to = datetime.fromtimestamp(int(request_args["to"])) if "to" in request_args else None
    if filter_from is not None and filter_to is not None:
        current_date_range_display = "{} to {}".format(filter_from.strftime("%Y-%m-%d %H:%M:%S"), filter_to.strftime("%Y-%m-%d %H:%M:%S"))
    elif filter_from is not None or filter_to is not None:
        current_date_range_display = (filter_from or filter_to).strftime("%Y-%m-%d %H:%M:%S")
    else:
        current_date_range_display = ""

    return flask.render_template(
        "messages.html",
        messages=messages,
        channels=channels,
        users=users,
        request_args=request_args,
        sort_type=flask.request.args.get("sort", "time-ascending"),

        slack_team_domain=SLACK_TEAM_DOMAIN,

        first_page_url=first_page_url,
        previous_page_url=previous_page_url,
        next_page_url=next_page_url,
        last_page_url=last_page_url,

        current_date_range_display=current_date_range_display,

        start_index=offset, end_index=offset + len(messages), message_count=message_count,
    )

@app.route("/api")
@slackegginess_required
def api():
    channel_info = {
        channel.channel_id: {
            "name": channel.channel_name,
            "purpose": channel.purpose,
        }
        for channel in Channel.query.all()
    }
    user_info = {
        user.user_id: {
            "name": user.user_name,
            "real_name": user.user_real_name,
            "is_bot": user.is_bot,
        }
        for user in User.query.all()
    }
    return jsonify(
        messages = "messages are available at the /api/messages endpoint",
        channels = channel_info,
        users    = user_info,
    )

@app.route("/api/messages")
@slackegginess_required
def api_messages():
    error_response, messages, message_count = retrieve_requested_messages(flask.request.args)
    if error_response is not None: return error_response

    # perform search
    return jsonify(
        message_count=message_count,
        messages=[
            {
                "timestamp": message.timestamp,
                "timestamp_order": message.timestamp_order,
                "user_id": message.user_id,
                "channel_id": message.channel_id,
                "value": message.value,
            }
            for message in messages
        ],
    )

if __name__ == "__main__":
    app.run(debug=True, port=5000) # debug mode
