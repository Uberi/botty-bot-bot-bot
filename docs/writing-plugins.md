Plugin Writing Guide
====================

Overview
--------

Botty plugins are simply Python classes. By convention, we organize these onto one class per file, and put these files under the `src/plugins` directory.

Plugin classes should inherit from the `BasePlugin` class (from `src/plugins/utilities.py`). This class provides basic functionality like sending messages, looking up user names, and so on.

Plugin classes can optionally implement the `on_step()` method, which is called on every time step (except in the situation described below) - generally several times a second. For multiple plugins, the `on_step` methods are called in the order that the plugins are registered.

If an plugin's `on_step` method returns a truthy value, all plugins registered after it will not have their `on_step` method called for that time step - returning a truthy value stops step processing for the current time step.

Plugin classes can optionally implement the `on_message(message)` method, which is called upon receiving a message (except in the situation described below). For multiple plugins, the `on_message` methods are called in the order that the plugins are registered, and always after `on_step` methods have been called.

If an plugin's `on_message` method returns a truthy value, all plugins registered after it will not have their `on_message` method called for that message - returning a truthy value stops message processing for the current message, representing that the message has been fully handled.

The `message` in `on_message(message)` is a JSON dictionary representing a Slack event. The format of this dictionary is documented in the [Slack API documentation](https://api.slack.com/rtm), under the "Events" section. Generally, most plugins will only care about the [message event type](https://api.slack.com/events/message).

However, it is a good idea to avoid accessing fields of the JSON dictionary directly if possible; if these change in the future, your code could break. If you just need the text, channel, or sender, use the `self.get_message_text(message)`, `self.get_message_channel(message)`, and `self.get_message_sender(message)` methods instead.

Plugins can interact with messages easily using the `self.say` (say something) and `self.react` (react to a message) methods. In message handlers, the `self.respond` (respond to the most recent message) and `sely.reply` (react to the most recent message) methods can be used instead, which are a bit easier to use. Make sure to read the "Types of Text" section to format messages correctly, especially things like URLs and username references.

A Simple Plugin
---------------

Here is an echo plugin, which simply repeats every message back in the channel that it was sent in. To try this out, save the code as `src/plugins/echo.py`:

```python
from .utilities import BasePlugin
class EchoPlugin(BasePlugin):
    def __init__(self, bot): super().__init__(bot) # initialize the plugin
    def on_message(self, message):
        sendable_text = self.get_message_text(message) # get the message text, or `None` for messages that don't have text associated with them
        if sendable_text is None: return False
        self.respond(sendable_text) # repeat the message in the same channel
        return True # mark message as handled, which prevents it from being further processed by other plugins
```

Plugins are just Python classes, so we also need to register them with Botty. For the echo plugin above, update the body of the `initialize_plugins` function in `src/botty.py`:

```python
def initialize_plugins(botty):
    # ...all the plugins that should receive messages before the echo plugin...
    from plugins.echo import EchoPlugin; botty.register_plugin(EchoPlugin(botty))
    # ...all the plugins that should receive messages after the echo plugin...
```

Why does registering a plugin with Botty require updating code, rather than Botty detect plugins automatically? Well, it's more explicit, allows temporary disabling of plugins (by commenting out lines), and avoids messy configuration files.

Message Flows
-------------

Sometimes, you'll want a plugin that handles multiple messages in a stateful way. For example, consider a questionnaire plugin - when the user says "questions", the plugin asks a few questions before replying with a message. The most obvious way to implement this is to use a state machine:

```python
from .utilities import BasePlugin
class QuestionsPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.questions_state = {}
        self.questions_answer_1, self.questions_answer_2, self.questions_answer_3 = {}, {}, {}

    def on_message(self, message):
        text, channel, user_id = self.get_message_text(message), self.get_message_channel(message), self.get_message_sender(message)
        if "questions" in text:
            self.questions_state[(channel, user_id)] = "QUESTION_1"
            self.respond("<@{}>, do you enjoy gardening?".format(user_id))
            return True
        if self.questions_state.get((channel, user_id)) == "QUESTION_1" and text in {"yes", "no"}:
            self.questions_state[(channel, user_id)] = "QUESTION_2"
            self.questions_answer_1[(channel, user_id)] = text
            self.respond("<@{}>, what's your favourite additive primary color?".format(user_id))
            return True
        if self.questions_state.get((channel, user_id)) == "QUESTION_2" and text in {"red", "green", "blue"}:
            self.questions_state[(channel, user_id)] = "QUESTION_3"
            self.questions_answer_2[(channel, user_id)] = text
            self.respond("<@{}>, what number between 1 and 5 inclusive am I thinking of?".format(user_id))
            return True
        if self.questions_state.get((channel, user_id)) == "QUESTION_3" and text in {"1", "2", "3", "4", "5"}:
            del self.questions_state[(channel, user_id)]
            answer_1, answer_2, answer_3 = self.questions_answer_1[(channel, user_id)], self.questions_answer_2[(channel, user_id)], text
            self.respond("<@{}>, you {} gardening, like the color {}, and guessed the number {}".format(user_id, "enjoy" if answer_1 == "yes" else "don't enjoy", answer_2, answer_3))
            return True
        return False
```

This does work, but because of the need to manage the questionnaire state, the actual logic is hard to parse. Instead, we can use the `Flow` class from `src/plugins/utilities.py`. This class allows you to write a complex message state machine as a single generator function. Here is the exact same plugin, modified to use `Flow`:

```python
from .utilities import BasePlugin, Flow
class QuestionsPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.questions_flow = Flow(self.run_questions)

    def run_questions(self, user_id): # generator function to demonstrate multi-message flows
        self.respond("<@{}>, do you enjoy gardening?".format(user_id))
        answer_1 = yield True # yield True because we successfully handled the message that started this flow
        while answer_1 not in {"yes", "no"}: answer_1 = yield False # keep ignoring user messages until it's one we expect

        self.respond("<@{}>, what's your favourite additive primary color?".format(user_id))
        answer_2 = yield True # yield True because we successfully handled answer 1, and get the user's next message as well
        while answer_2 not in {"red", "green", "blue"}: answer_2 = yield False # keep ignoring user messages until it's one we expect

        self.respond("<@{}>, what number between 1 and 5 inclusive am I thinking of?".format(user_id))
        answer_3 = yield True # yield True because we successfully handled answer 2, and get the user's next message as well
        while answer_3 not in {"1", "2", "3", "4", "5"}: answer_3 = yield False # keep ignoring user messages until it's one we expect

        self.respond("<@{}>, you {} gardening, like the color {}, and guessed the number {}".format(user_id, "enjoy" if answer_1 == "yes" else "don't enjoy", answer_2, answer_3))
        return True # return True because answer 3 we successfully handled answer 3

    def on_message(self, message):
        text, channel, user_id = self.get_message_text(message), self.get_message_channel(message), self.get_message_sender(message)
        if "questions" in text: # start the questionnaire
            self.questions_flow.start((channel, user_id), user_id) # start the flow - run the generator up to the first yield
        return self.questions_flow.step((channel, user_id), text) # run the next step in the flow - this returns whatever value was yielded or returned from the generator function
```

With `Flow`, the logic is a lot easier to see: ask questions, wait for responses, then do something afterwards. For small examples like this one, the code is still about the same length, but for more complicated flows, the `Flow` class can make your code significantly shorter and more readable.

What is a flow key? A flow key represents the thing that each individual generator iterator is associated with. For example, `QuestionsPlugin` above uses channel and user ID tuples as its flow key. That means there can be a unique questionnaire for each combination of users and channels - each user can have their own instance of the questionnaire, in every channel.

When does each part of the generator function run? The part before the first `yield` is run upon calling `some_flow_instance.start(...)`. Each call to `some_flow_instance.step(...)` will run the next piece of code between `yield` or `return` statements. Note that there can be multiple generator iterators resulting from a single generator function all running at once; each flow has one generator function, but can also have one generator iterator for every flow key. For example, if the flow keys are channels, then there can be one generator iterator for each channel.

What should the generator function return/yield each time? The general rule is "return a truthy value if and only if the previous return value of `yield` was successfully handled (or if there is no previous `yield`)". So the first `yield` in the function should generally be `yield True`, because there was no previous `yield`. Note that `return SOME_VALUE` and `yield SOME_VALUE` have exactly the same meaning, except the former also ends the flow.

Why do we often return the value of `some_flow_instance.step(...)` at the end of our `on_message` methods? When the generator function returns or yields a value, this is because we called `some_flow_instance.step(...)` to send in some data. `some_flow_instance.step(...)` will then return that returned/yielded value from the generator function, which represents whether the flow successfully handled the sent-in data. If the sent-in data represents a single message, the return value then means "whether the flow handled the message". Note that if you have multiple concurrent flows and the sent-in data for each one represents a single message, you can return `any(flow_instance.step(...) for flow_instance in list_of_flow_instances)`, which means "whether any of the flows handled the message".

Here's another example of `Flow`, demonstrating more complex multi-message interactions. When a user says "barrier", the plugin activates a barrier, and then waits for 5 different people to say "ready" before responding with a message:

```python
from .utilities import BasePlugin
class BarrierPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)
        self.barrier_flow = Flow(self.run_barrier)
        self.barrier_size = 5 # this many people must be ready before we can proceed

    def run_barrier(self, extra_data): # generator function to demonstrate mutli-message flows
        self.respond_raw("No people ready; barrier holding")
        ready_users = set()
        while len(ready_users) < self.barrier_size:
            text, user = yield True # yield True because we successfully handled the last-retrieved message, and get the user's next message as well
            while "ready" not in text: text, user = yield False # keep ignoring user messages until it's one we expect
            ready_users.add(user) # mark the user as ready
            self.respond_raw("{} people ready; barrier holding".format(len(ready_users)))
        self.respond_raw("Party ready; barrier released!") # 5 different people have said "ready"
        return True # return True because we successfully handled the last "ready" message

    def on_message(self, message):
        text, channel, user = self.get_message_text(message), self.get_message_channel(message), self.get_message_sender(message)
        if "barrier" in text:
            if self.barrier_flow.is_running(channel): # don't allow a new barrier to be activated if there already is one
                self.respond("There's already a barrier active!")
                return True
            self.barrier_flow.start(channel)
        return self.barrier_flow.step(channel, (text, user)) # this returns whatever value was yielded or returned from the generator function
```

Types of Text
-------------

There are actually three different formats for text in Slack messages:

* **Sendable format** is the format of text that is suitable for sending as the body of messages in the Slack API, such as for message contents.
    * **Sendable text** is text that follows the sendable format.
    * Sendable text should generally be considered opaque, since you generally won't want to go through the effort of dealing with the syntax.
    * The main difference between sendable text and server text is that sendable text has bare links, while server text surrounds links with `<` and `>`.
    * That means that if you send server text instead of sendable text, links will have angle brackets around them.
* **Plain format** is the lack of any fixed format.
    * **Plain text** is text that has no fixed format - it can contain anything.
    * The main difference between plain text and sendable text is that sendable text has the `<`, `>`, and `&` characters HTML-escaped, while plain text does not.
* **Server format** is the format of text received from the Slack API, such as for message contents.
    * **Server text** is text that follows server format.
    * Plugins generally don't have to care about server text because functions in the plugin API that deal with text will return either sendable or plain text.

Sendable text should be used for sending back parts of Slack messages that we receive, and plain text should be used for everything else. This is because **sendable text can represent more information than plain text can**, such as channel/user references, links, and more. Therefore, **converting sendable text to plain text can lose information**.

However, **sendable text has special formatting that needs to be explicitly handled in code**. For things like sending the text to a search engine as a query, it is better to send the plain text version, since it will not have any of the special formatting.

For example, if someone messages "@onthono in #general" (a username reference and a channel reference) to Botty, Botty might receive the sendable text `<@U123456> in <#C123456>`. If you convert this to plain text, it becomes `@onthono in #general`, as you would expect. In other words, **the plain text version of a message is what a user would type to send that message, while the sendable text version is what the server actually sees**.

Suppose we have a plugin that attempts to evaluate all messages as Python code and responds with the results:

```python
from .utilities import BasePlugin
class ArithmeticPlugin(BasePlugin):
    def __init__(self, bot):
        super().__init__(bot)

    def on_message(self, message):
        sendable_text = self.get_message_text(message)
        if sendable_text is None: return False
        text = self.sendable_text_to_text(sendable_text) # convert sendable text to plain text

        try: result = str(eval(text)) # we evaluate the plain text `text` rather than the sendable text `sendable_text`
        except Exception as e: result = str(e)
        sendable_result = self.text_to_sendable_text(result)

        # we send `sendable_text` instead of `text` to preserve sendable formatting that is lost when converting sendable text to plain text
        self.respond("{} :point_right: {}".format(sendable_text, sendable_result))
        return True
```
