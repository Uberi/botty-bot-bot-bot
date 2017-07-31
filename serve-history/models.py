import re
from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.event import listens_for
from cachetools import TTLCache, cached

db = SQLAlchemy()

class Message(db.Model):
    __tablename__ = "messages"
    timestamp = db.Column(db.Integer, primary_key=True)
    timestamp_order = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Text, db.ForeignKey("users.user_id"), nullable=False)
    channel_id = db.Column(db.Text, db.ForeignKey("channels.channel_id"), nullable=False)
    user = db.relationship("User", backref=db.backref("messages", lazy=True))
    channel = db.relationship("Channel", backref=db.backref("messages", lazy=True))
    value = db.Column(db.Text)
    channel_offset = db.Column(db.Integer)
    def __init__(self, timestamp, timestamp_order, user_id, channel_id, value):
        self.timestamp, self.timestamp_order, self.user_id, self.channel_id, self.value = timestamp, timestamp_order, user_id, channel_id, value
    def __repr__(self): return "<Message at {}>".format(self.timestamp)
    def datetime(self): return datetime.fromtimestamp(self.timestamp)

class Channel(db.Model):
    __tablename__ = "channels"
    channel_id = db.Column(db.Text, primary_key=True)
    channel_name = db.Column(db.Text)
    purpose = db.Column(db.Text)
    def __init__(self, channel_id, channel_name, purpose):
        self.channel_id, self.channel_name, self.purpose = channel_id, channel_name, purpose
    def __repr__(self): return "<Channel {}>".format(self.channel_name)

class User(db.Model):
    __tablename__ = "users"
    user_id = db.Column(db.Text, primary_key=True)
    user_name = db.Column(db.Text)
    user_real_name = db.Column(db.Text)
    is_bot = db.Column(db.Integer)
    def __init__(self, user_id, user_name, user_real_name, is_bot):
        self.user_id, self.user_name, self.user_real_name, self.is_bot = user_id, user_name, user_real_name, is_bot
    def __repr__(self): return "<User {}>".format(self.user_name)

def sqlite_regexp(pattern, string):
    """According to the [SQLite3 docs](https://sqlite.org/lang_expr.html), `X REGEXP Y` is equivalent to `regexp(Y, X)`, so to implement custom regex matching, we define a custom SQL function in `initialize_db` called `regexp` that will get called by SQLite."""
    return re.search(pattern, string) is not None

def initialize_db(flask_app):
    db.init_app(flask_app)
    with flask_app.app_context():
        db.create_all()

        @listens_for(db.engine, "begin")
        def do_begin(conn):
            conn.connection.create_function("regexp", 2, sqlite_regexp)

result_counts_cache = TTLCache(maxsize=4096, ttl=60 * 10)  # cache for result counts where entries expire after 10 minutes
def get_messages(filter_from=None, filter_to=None, filter_channel_ids=None, filter_user_ids=None, filter_text=None, result_sort="time-ascending", result_offset=0, result_limit=1000):
    assert filter_from is None or isinstance(filter_from, int)
    assert filter_to is None or isinstance(filter_to, int)
    assert filter_channel_ids is None or isinstance(filter_channel_ids, frozenset)
    assert filter_user_ids is None or isinstance(filter_user_ids, frozenset)
    assert filter_text is None or isinstance(filter_text, str)
    result = Message.query
    if filter_from is not None:
        result = result.filter(Message.timestamp >= filter_from)
    if filter_to is not None:
        result = result.filter(Message.timestamp <= filter_to)
    if filter_channel_ids is not None:
        result = result.filter(Message.channel_id.in_(filter_channel_ids))
    if filter_user_ids is not None:
        result = result.filter(Message.user_id.in_(filter_user_ids))
    if filter_text is not None:
        result = result.filter(Message.value.op("regexp")(filter_text))

    if result_sort == "time-ascending":
        result = result.order_by(Message.timestamp.asc(), Message.timestamp_order.asc())
    elif result_sort == "time-descending":
        result = result.order_by(Message.timestamp.desc(), Message.timestamp_order.desc())
    elif result_sort == "channel-ascending":
        result = result.join(Message.channel).order_by(Channel.channel_name.asc())
    elif result_sort == "channel-descending":
        result = result.join(Message.channel).order_by(Channel.channel_name.desc())
    elif result_sort == "user-ascending":
        result = result.join(Message.user).order_by(User.user_name.asc())
    elif result_sort == "user-descending":
        result = result.join(Message.user).order_by(User.user_name.desc())

    # retrieve the current page of messages
    # we try to retrieve an extra message right after the last requested message, to determine whether there should be a next page or not
    # this extra message is removed if there is a next page
    messages = result.offset(result_offset).limit(result_limit + 1).all()
    has_next_page = len(messages) == result_limit + 1
    if has_next_page: messages.pop()

    # count results if it hasn't been counted recently
    filters_key = (filter_from, filter_to, filter_channel_ids, filter_user_ids, filter_text)
    if filters_key in result_counts_cache:
        count = result_counts_cache[filters_key]
    else:
        count = result.count()
        result_counts_cache[filters_key] = count

    return messages, count