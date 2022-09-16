# Fork information
## Added features
- [!import_path [&lt;path&gt;]](#import_path-path)
- [!import_all &lt;path&gt;](#import_all-path)
- [Channel creation](#channel-creation)
- [Mentions and User mapping](#mentions-and-user-mapping)
- [File-attachments](#file-attachments)
- [Splitting messages](#splitting-messages)

### !import_path [&lt;path&gt;]
Added a command that allows user to call the bot from a different channel, where the target channel's name is extracted from given path.

### !import_all &lt;path&gt;
Added a command that parses given slack log directory and imports *all* channels found within.
Unlike *import_path*, this command forces the path into the slack-log's root-folder (if possible) even if user targeted a subdirectory or specific file.

### Channel creation
If a migrated channel does not exist, it is created.
For import_all this step happens for all channels before migrating their contents, so they exist when encountering channel-mentions.

### Mentions and User mapping
Mentions were fixed, such that they attempt to translate to an actual discord-mention.
To achieve this the targeted user has to be found, which is fascilitated by a slack2discord_users.json file containing username-mappings.
If a user does not have a mapping, their slack-name is used instead.
If a user is not found (mapped or not), it defaults to a regular string f"@{slack_name}".
Note that mapping to a user to an empty string can be used to force the user to not be found.

### File-attachments
Added the ability to parse file-attachments in slack messages, and creates Embed's for them in discord.
Note that it does not download the Files and upload to discord. Meaning the files themselves remain on slack.

### Splitting messages
When a message exceeds discords character limit, it is split into multiple messages.
Each message references their parent in the chain.
If there are multiple embeds in a single message, they are split into multiple messages.
If there was a message body, the first embed is attached to the message, and any additional embeds reference that message. If message's text was split, the last in the chain is used.
If discord.py version >= v2.0, it tries to attach 10 (API limit) embeds to each message instead.

## Features from original/upstream
### !import_here [&lt;path&gt;]
A command importing the .json logs found inside given path into the current channel.

### Mapping uid's to slack-name
When encountering a uid in a message, it is mapped to the slack-name.
Same is done for channels.

### Message header
When migrating a message, the bot prefixes a header of who sent it and when.

## Features that are NOT implemented
### Migrating files
The file-attachments are not actually reuploaded into discord, but merely posted as an Embed linking to the file's url.

### Migrating Threads
Slack threads are not properly migrated into discord threads.
Messages from a thread is posted (chronologically) into their parent channel instead.

### Migrating DMs
The bot is unable to migrate DMs, on account of slack not exporting DMs.
Even if slack did, the bot would not have access to all discord-user's accounts, and would thus be unable to send DMs from them.

### Messages looking like they are posted from user instead of bot
While it does append the header, when migrating messages the bot does **not** make them appear as if the appropriate user posted them.

### Querying user and command arguments
No command arguments can be given when starting the bot, and the user is not queried for mappings if they failed to create a slack2discord_users.json file.


# slack2discord (original/upstream's README.md)
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
1. Invoke ``!import_here <filepath>`` from Discord in whichever channel you want to import the messages to. Note that if your path contains spaces, you must surround the path with quotes (e.g., ``!import_here "c:\path\to\some file"``). You may also pass multiple paths to import multiple Slack channels into a single Discord channel (e.g. ``!import_here c:\path\to\channel1 c:\path\to\channel2``).