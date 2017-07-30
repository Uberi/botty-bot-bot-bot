Botty Bot Bot Bot
=================
Personable chatbot for [Slack](https://slack.com/) using the [Slack Realtime Messaging API](https://api.slack.com/rtm).

Features
--------

* **Debug mode with Botty Slack Simulation Environment**: interact with, test, and debug Botty and Botty plugins locally on the command line, without using Slack at all.
* In-process **Python REPL**: monitor, patch, or control running Botty instances **without restarting** or editing files.
* Excellent **Slack feature support**: supports reactions, threads/replies, message edits/deletions, and so on.
* Simple and reliable: Botty gracefully handles **plugin exceptions**, **network issues**, and more.
* Robust **plugin API**: friendly error messages and well-documented functions makes development fast and productive - each plugin is simply a Python class.
* Strong **Slack protocol compliance**: supports periodic ping, message escape sequences, and more, on top of the official Slack Python library.

Deployment
----------

From a fresh new t2.micro instance on AWS EC2 with a new 16GB EBS volume:

1. SSH into the machine: `ssh ec2-user@ec2-34-213-63-151.us-west-2.compute.amazonaws.com`.
2. Run software updates: `sudo yum update`.
3. In `/etc/ssh/sshd_config`, change `Port` to `48372` and `PasswordAuthentication` to `no` and `PermitRootLogin` to `no` and `AllowUsers` to `ec2-user`. Restart `sshd` using `sudo service sshd restart`.
4. Stop unnecessary services: `sudo service sendmail stop`.
5. Get requirements: `sudo yum install git python35 python35-pip`.
6. Use a virtualenv: `sudo python3 -m pip install virtualenv`, `virtualenv venv`, `source ./venv/bin/activate`.
7. Transfer over existing Slack history into the `@history` folder.

Various plugin setup procedures:

* Haiku
* Markov chains
* Spaaace

To test locally, run `python3 src/botty.py` in the terminal:

    $ ./src/botty.py
    No Slack API token specified in command line arguments; starting in local debug mode...

    ##########################################
    #   Botty Slack Simulation Environment   #
    ##########################################

    This is a local chat containing only you and Botty. It's useful for testing and debugging.

    The following slash commands are available:

        /react -3 eggplant        | reacts to the third most recent text message with an eggplant
        /unreact 1 heart          | removes the heart reaction from the second earliest text message
        /reply -1 yeah definitely | replies to the most recent text message with "yeah definitely"
        /channel random           | moves you and Botty to the #random channel

    #general    | Me: hello
    #general    | Me: calc integrate(1/x, x)
    #general    | Botty: integrate(1/x, x) :point_right: log(x)
    #general    | Me: /reply -1 threads work too :O
    #general    | Me (in thread for "integrate(1/x, x) :point_right: log(x)"): threads work too :O
    #general    | Me: where are the eggplants?
    #general    | Botty reacted to "where are the eggplants?" with :eggplant:
    #general    | Me: biggify hello
    #general    | Botty: ```
          ___           ___           ___       ___       ___     
         /\__\         /\  \         /\__\     /\__\     /\  \    
        /:/  /        /::\  \       /:/  /    /:/  /    /::\  \   
       /:/__/        /:/\:\  \     /:/  /    /:/  /    /:/\:\  \  
      /::\  \ ___   /::\~\:\  \   /:/  /    /:/  /    /:/  \:\  \ 
     /:/\:\  /\__\ /:/\:\ \:\__\ /:/__/    /:/__/    /:/__/ \:\__\
     \/__\:\/:/  / \:\~\:\ \/__/ \:\  \    \:\  \    \:\  \ /:/  /
          \::/  /   \:\ \:\__\    \:\  \    \:\  \    \:\  /:/  / 
          /:/  /     \:\ \/__/     \:\  \    \:\  \    \:\/:/  /  
         /:/  /       \:\__\        \:\__\    \:\__\    \::/  /   
         \/__/         \/__/         \/__/     \/__/     \/__/```
    #general    | Me: 

To run in production mode, run `python3 src/botty.py SLACK_API_TOKEN_GOES_HERE`, where `SLACK_API_TOKEN_GOES_HERE` is the Slack API token (obtainable from the [Slack API site](https://api.slack.com/)). Alternatively, edit `example-start-botty.sh` to replace `SLACK_API_TOKEN_GOES_HERE` with the Slack API token, then run `./example-start-botty.sh`.

Currently, a Botty instance is deployed for [nokappa.slack.com](https://nokappa.slack.com/) on EC2 inside a [tmux](https://tmux.github.io/) session, to allow monitoring and management over SSH. Code updates are done via Git.

Developing Botty
----------------

See the "Deployment" section for information about setting up an environment suitable for developing Botty with.

Botty ships with several plugins by default, some of which require API keys or take some time to start. If you don't need those plugins, simply comment out the relevant lines in the body of the `initialize_plugins` function in `src/botty.py` to disable them.

See the [code reference](https://github.com/Uberi/botty-bot-bot-bot/blob/master/docs/reference.md) for API documentation, project file layout, and more.

See the [plugin writing guide](https://github.com/Uberi/botty-bot-bot-bot/blob/master/docs/writing-plugins.md) for information about how to develop your own Botty plugins.

License
-------

Copyright 2015-2017 [Anthony Zhang (Uberi)](https://anthony-zhang.me).

The source code is available online at [GitHub](https://github.com/Uberi/botty-bot-bot-bot).

This program is made available under the MIT license. See ``LICENSE.txt`` in the project's root directory for more information.
