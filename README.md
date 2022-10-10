# slack2discord
Tool for importing Slack message history into Discord

## Usage
slack2discord is meant to be a one-time-use bot for importing a message history from Slack. Follow the steps below to install, execute, and invite the bot to your server. Once it's invited, use the ``!import_here <filepath>`` command to start the import process from the file specified (relative to the bot) to the channel from which the command was invoked. Note that Discord limits the rate at which messages can be sent to a server so this bot is intentionally slow.

## Exporting Messages from Slack
Slack allows for you to export all messages from your workspace. See [Slack's official documentation](https://slack.com/help/articles/201658943-Export-your-workspace-data) for details. The exported files will be organized into individual directories for each channel with .json files for each day's messages. slack2discord can handle individual .json files or entire channel directories.

---
### **NOTE**

Add a file _slack2discord_users.json_ in the root directory, that can be used to map between the slack user and their respective nicknames. 

#### OR 

Just leave an empty _slack2discord_users.json_ file in the root directory with other JSON files (_channels.json_,_users.json_,_integration_logs.json_).

---

## Executing the Program
1. Clone this repository and set up any appropriate virtual environment.
1. Use ``pip install -r requirements.txt`` to install the necessary requirements. Alternatively, just install discord.py with ``pip install discord.py``
1. Execute the program.
1. Enter the bot token as prompted by the program.
1. Invoke one of the import functions below from within Discord. Note that if your path contains spaces, you must surround the path with quotes (e.g., ``!import_all "c:\path\to\some file"``).

## Features
- [!import_path &lt;path&gt;](#import_path-path)
- [!import_all &lt;path&gt;](#import_all-path)
- [Thread Migration](#thread-migration)
- [Channel Creation](#channel-creation)
- [Mentions and User Mapping](#mentions-and-user-mapping)
- [File Attachments](#file-attachments)
- [Splitting Messages](#splitting-messages)

### !import_path &lt;path&gt;
Allows user to call the bot from a different channel, where the target channel's name is extracted from given path.

### !import_all &lt;path&gt;
Parses given Slack log directory and imports *all* channels found within.
Unlike *import_path*, this command forces the path into the Slack log's root directory (if possible) even if user targeted a subdirectory or specific file.

### Thread Migration
Slack threads are migrated into equivalent discord Threads *if discord.py version >= 2.0*.
If not, they are instead migrated in the form of a reply to the Thread OP, adding a thread-prefix to the message header. 

### Channel & Thread Creation
If a migrated channel or thread does not exist, it is created.
For the `import_all` command all channels are checked *before* migrating their contents, so they exist when encountering channel mentions.

### Mentions and User Mapping
Mentions translate to an actual Discord mention.
To achieve this the targeted user has to be found, which is fascilitated by a slack2discord_users.json file containing username mappings.
If a user does not have a mapping, their Slack name is used instead.
If a user is not found (mapped or not), it defaults to a regular string f"@{slack_name}".
Note that mapping a user to an empty string can be used to force the user to not be found.

### File Attachments
File attachments are parsed from Slack messages and translatd to an embed for them in Discord.
Note that it does not download the actual files and upload them to Discord. The files themselves remain on Slack.

### Splitting Messages
When a message exceeds Discord's character limit, it is split into multiple messages.
Each message references their parent in the chain.
If there are multiple embeds in a single message, they are split into multiple messages.
If there was a message body, the first embed is attached to the message, and any additional embeds reference that message. If message's text was split, the last in the chain is used.
If discord.py version >= v2.0, it tries to attach (up to) 10 embeds (API limit) to each message instead.

## Deprecated Features
### !import_here &lt;path&gt;
A command for importing the .json logs found inside given path into the current channel.
When encountering a uid or channel in a message, it is mapped to the Slack name.
When migrating a message, the bot prefixes a header of who sent it and when.

## Features that are NOT Implemented
### Migrating Files
The file attachments are not actually reuploaded into discord, but merely posted as an Embed linking to the file's url.

### Migrating DMs
The bot is unable to migrate DMs, on account of Slack not exporting DMs.
Even if Slack did, the bot would not have access to all Discord user's accounts, and would thus be unable to send DMs from them.

### Messages looking like they are posted from user instead of bot
While it does append the header, when migrating messages the bot does **not** make them appear as if the appropriate user posted them.

### Querying user and command arguments
No command arguments can be given when starting the bot, and the user is not queried for mappings if they failed to create a slack2discord_users.json` file. The only query performed is for the bot-token.
