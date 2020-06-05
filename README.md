# slack2discord
Tool for importing Slack message history into Discord

## Usage
slack2discord is meant to be a one-time-use bot for importing a message history from Slack. Follow the steps below to install, execute, and invite the bot to your server. Once it's invited, use the ``!import_here <filepath>`` command to start the import process from the file specified (relative to the bot) to the channel from which the command was invoked. Note that Discord limits the rate at which messages can be sent to a server so this bot is intentionally slow.

## Exporting Messages from Slack
Slack allows for you to export all messages from your workspace. See [Slack's official documentation](https://slack.com/help/articles/201658943-Export-your-workspace-data) for details. The exported files will be organized into individual directories for each channel with .json files for each day's messages. slack2discord can handle individual .json files or entire channel directories.

## Executing the Program
1. Clone this repository and set up any appropriate virtual environment.
1. Use ``pip install -r requirements.txt`` to install the necessary requirements. Alternatively, just install discord.py with ``pip install discord.py``
1. Execute the program.
1. Enter the bot token as prompted by the program.
1. Invoke ``!import_here <filepath>`` from Discord in whichever channel you want to import the json files to.