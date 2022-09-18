#!/usr/bin/env python3
# Authors: Rocky Slavin
#          Felix Hallqvist
# Slack message history importer for Discord
# Note that some functionality won't work properly if not using the import_all command,
# such as messages in threads created in older .json logs (created in the text channel instead),
# or referencing channels not created yet.
# Also note that mentions will only be properly migrated for users already on the discord server.
# To fascilitate the fact that people use different nicks, there is a slack2discord.json file where you can map those (if no mapping exists, it just attempts to match name).
# TODO Properly migrate the assets to discord, rather than embedded url's
# TODO Post messages looking like the mapped user (webhooks? send() can specify username there)
import json
import sys
import os
import time
from datetime import datetime
import discord
from discord.ext import commands

MAX_EMBEDS = 1
if discord.__version__[0] >= "2":
    MAX_EMBEDS = 10

MAX_CHARACTERS = 2000

THROTTLE = True
THROTTLE_TIME_SECONDS = 0.1


def check_optional_dependencies():
    print(f"[INFO] Checking (optional) dependency versions:")
    if discord.__version__[0] < "2":
        # Pre discord.py v2.0 the bot can only give messages 1 embed,
        #  so has to be split into multiple messages.
        # Creating threads was added in discord.py v2.0
        # discord.py v2.0 also increased the package's requirements,
        #  requiring a higher python version.
        # It is thus treated as optional.
        print(f"[WARNING] discord.py version < 2.0, currently using version: {discord.__version__}")
        print(f"          Some features are unsupported with current version:")
        print(f"          * Unable to create Threads")
        print(f"            - Messages will be sent directly to the owner's TextChannel instead.")
        print(f"          * Messages are unable to contain more than 1 Embed each")
        print(f"            - Multiple attachments they will be split into multiple messages,")
        print(f"               linking to their 'parent' message.")
        print(f"          Upgrade discord.py to >= 2.0 to enable those features.")
        
        if sys.version_info[1] < 8:
            print(f"[INFO] Current python version does not satisfy discord.py v2.0 dependency. Current: {'.'.join(map(str, sys.version_info[:3]))}")
            print(f"       You will be unable to upgrade discord.py to v2.0,")
            print(f"        unless you first upgrade python to >= 3.8")
    else:
        print(f"       All features enabled! - No dependencies unsatisfied")
    print(f"")


def get_basename(file_path):
    if os.path.basename(file_path):
        return os.path.basename(file_path)
    else: # 'foo/bar/' has no basename, but os.path.split strips trailing slash and returns 'foo/bar'
        return os.path.basename(os.path.split(file_path)[0])


def get_filename(file_path):
    return get_basename(os.path.splitext(file_path)[0])


def parse_slack_directory(file_path, force_all=False):
    """
    Returns a dict with paths to the important files,
    and a dict of paths to history files mapped as {"channel": [files]}.
    :param file_path: String path to directory or file
    :return: Dict with paths to all json files.
    """
    root = file_path
    
    important_files = [
        "users.json",
        "slack2discord_users.json",
        "channels.json",
        "integration_logs.json"
    ]
    if force_all is True:
        if not all([os.path.exists(os.path.join(root, f)) for f in important_files]):
            print(f"[WARNING] Path does not point at the root of a slack-log directory: {file_path}")
            print(f"[FIX] Assume path points at a file or subdirectory")
            root = os.path.dirname(root)
            if not all([os.path.exists(os.path.join(root, f)) for f in important_files]):
                print(f"[WARNING] Path does not point at a file or subdirectory")
                print(f"[FIX] Assume path points at some file inside subdirectory")
                root = os.path.dirname(root)
                if not all([os.path.exists(os.path.join(root, f)) for f in important_files]):
                    print(f"[ERROR] Path does not point at some file inside subdirectory - skipping path.")
                    return None

    slack_dir = {}
    slack_dir["history"] = {}
    slack_dir["important"] = {get_filename(f): f for f in important_files}
    
    if all([os.path.exists(os.path.join(root, f)) for f in important_files]):
        subdirs = [d for d in [os.path.join(root, n) for n in os.listdir(root)] if os.path.isdir(d)]
        for d in subdirs:
            slack_dir["history"][get_basename(d)] = [os.path.join(d, f) for f in os.listdir(d) if f.endswith(".json")]
    else:
        print(f"[WARNING] Path does not point at the root of a slack-log directory: {file_path}")
        print(f"[FIX] Assume path points at a channels subdirectory.")
        root = os.path.dirname(root)
        if os.path.isdir(file_path):
            slack_dir["history"][get_basename(file_path)] = [os.path.join(file_path, f) for f in os.listdir(file_path) if f.endswith(".json")]
        else:
            print(f"[WARNING] Path does not point at a directory.")
            print(f"[FIX] Assume path points at the exact .json log file user wants to restore.")
            if file_path.endswith(".json"):
                root = os.path.dirname(root)
                slack_dir["history"][os.path.dirname(file_path)] = [file_path]
            else:
                print(f"[ERROR] Path does not point at a .json file - skipping path.")
                return None
    
    slack_dir["important"] = {k: os.path.join(root, f) for k, f in slack_dir["important"].items() }
    slack_dir["root"] = root

    if not slack_dir["history"]:
        print(f"[ERROR] No history .json files found at: {file_path}")
    elif not all([os.path.exists(f) for f in slack_dir["important"].values()]):
        print(f"[ERROR] Missing important .json files: {({k: 'exists' if os.path.exists(f) else 'missing' for k, f in slack_dir['important'].items()})}")
    else:
        print(f"[INFO] {len(slack_dir)} .json files loaded")

    return slack_dir


def get_display_names(slack_dir):
    """
    Generates a dictionary of user_id => display_name pairs
    :param slack_dir: Dict representing the slack-log directory
    :return: Dictionary or None if no file is found
    """
    users = {}

    print(f"[INFO] Attempting to locate users.json")

    file_path = slack_dir["important"]["users"]

    if not os.path.isfile(file_path):
        print(f"[ERROR] Unable to locate users.json: {file_path}")
        return None
    try:
        with open(file_path, encoding="utf-8") as f:
            users_json = json.load(f)
            for user in users_json:
                users[user['id']] = (
                    user['profile']['display_name'] if user['profile']['display_name'] else user['profile'][
                        'real_name'])
                print(f"\tUser ID: {user['id']} -> Display Name: {users[user['id']]}")
    except OSError as e:
        print(f"[ERROR] Unable to load display names: {e}")
        return None
    return users


def get_slack2discord_user_mapping(slack_dir):
    """
    Generates a dictionary of slack_user => discord_user
    :param slack_dir: Dict representing the slack-log directory
    :return: Dictionary or None if no file is found
    """
    slack2discord_users = {}

    print(f"[INFO] Attempting to locate slack2discord_users.json")
    
    file_path = slack_dir["important"]["slack2discord_users"]
    if not os.path.isfile(file_path):
        print(f"[ERROR] Unable to locate slack2discord_users.json: {file_path}")
        return None

    try:
        with open(file_path, encoding="utf-8") as f:
            slack2discord_users_json = json.load(f)
            for user in slack2discord_users_json:
                slack_name = user["slack"]["name"]
                discord_name = user["discord"]["name"]
                if user["discord"]["id"]:
                    discord_name = discord_name + f'#${user["discord"]["id"]}'
                slack2discord_users[slack_name] = discord_name
                print(f"\tslack2discord user mapping: {slack_name} -> {discord_name}")
    except OSError as e:
        print(f"[ERROR] Unable to load slack2discord user mapping: {e}")
        return None
    return slack2discord_users


def get_channel_names(slack_dir):
    """
    Generates a dictionary of channel_id => channel_name pairs
    :param slack_dir: Dict representing the slack-log directory
    :return: Dictionary or None if no file is found
    """
    channels = {}

    print(f"[INFO] Attempting to locate channels.json")

    file_path = slack_dir["important"]["channels"]
    if not os.path.isfile(file_path):
        print(f"[ERROR] Unable to locate channels.json: {file_path}")
        return None

    try:
        with open(file_path, encoding="utf-8") as f:
            channels_json = json.load(f)
            for channel in channels_json:
                channels[channel['id']] = channel['name']
                print(f"\tChannel ID: {channel['id']} -> Channel Name: {channels[channel['id']]}")
    except OSError as e:
        print(f"[ERROR] Unable to load channel names: {e}")
        return None
    return channels

async def fill_references(ctx, message, users, slack2discord_users, channels):
    """
    Fills in @mentions and #channels with their known display names
    :param message: Raw message to be filled with usernames and channel names instead of IDs
    :param users: Dictionary of user_id => display_name pairs
    :param channels: Dictionary of channel_id => channel_name pairs
    :return: Filled message string
    """
    for uid, slack_name in users.items():
        old_str = f"<@{uid}>"
        if old_str in message and slack_name:
            new_str = f"@{slack_name}"
            if slack_name in slack2discord_users:
                discord_name = slack2discord_users[slack_name]
                discord_user = ctx.guild.get_member_named(discord_name)
                if discord_user:
                    new_str = f"{discord_user.mention}"
                else:
                    print(f"[ERROR] Mapped user not found on discord: [{slack_name}: {discord_name}]")
                    print(f"        @mentions of user will not be translated to discord-equivalent")
            else:
                print(f"[WARNING] User not mapped: {slack_name}")
                print(f"[FIX] Attempt to match the slack name instead")
                discord_user = ctx.guild.get_member_named(slack_name)
                if discord_user:
                    new_str = f"{discord_user.mention}"
                else:
                    print(f"[ERROR] User not found on discord: {slack_name}")
                    print(f"        @mentions of user will contain their ID instead of display name")
            
            message = message.replace(old_str, new_str)
    for cid, name in channels.items():
        old_str = f"<#{cid}>"
        if old_str in message:
            new_str = f"#{name}"
            channel = discord.utils.get(ctx.guild.channels, name=name)
            if channel:
                new_str = f"{channel.mention}"
            else:
                print(f"[ERROR] Channel not found on discord: {name}")
                print(f"        #channel references of channel will not be translated to discord-equivalent")

            message = message.replace(old_str, new_str)
    return message


def parse_important_files(slack_dir):
    users = get_display_names(slack_dir)
    if users:
        print(f"[INFO] users.json found - attempting to fill @mentions")
    else:
        print(f"[WARNING] No users.json found - @mentions will contain user IDs instead of display names")

    slack2discord_users = get_slack2discord_user_mapping(slack_dir)
    if slack2discord_users:
        print(f"[INFO] slack2discord_users.json found - attempting to map @mentions")
    else:
        print(f"[WARNING] No slack2discord_users.json found.")
        print(f"[FIX] Querying user for known mappings to generate file") # TODO
        print(f"[ERROR] Querying feature not implemented - @mentions will not map")

    channels = get_channel_names(slack_dir)
    if channels:
        print(f"[INFO] channels.json found - attempting to fill #channel references")
    else:
        print(f"[WARNING] No channels.json found - #channel references will contain their IDs instead of names")
    
    return users, slack2discord_users, channels


async def get_or_create_channel(ctx, name):
    channel = discord.utils.get(ctx.guild.channels, name=name, type=discord.ChannelType.text)
    if not channel:
        print(f"[INFO] Could not find channel: {name}")
        print(f"       Creating channel")
        channel = await ctx.guild.create_text_channel(name, reason="Migrating Slack channel")
    return channel


def parse_timestamp(message):
    if 'ts' in message:
        return datetime.fromtimestamp(float(message['ts'])).strftime('%d/%m/%Y at %H:%M:%S')
    else:
        print(f"[WARNING] No timestamp in message")
    return '<no timestamp>'


def parse_user(message, users):
    username = "<unknown user>"
    user = message.get('user_profile')
    if user:
        keys = ['display_name','name','real_name'] # username keys (ordered by priority)
        present_keys = [k for k in keys if user.get(k)] # `k in user` would accept empty fields
        if present_keys:
            username = user[present_keys[0]]
        else:
            print(f"[ERROR] Unable to parse user: {user}")
    else:
        print(f"[WARNING] No 'user_profile' field in message")
        print(f"[FIX] Attempting 'user' field for uid")
        if "user" in message:
            print(f"[INFO] Located 'user' field, attempting to map uid to username")
            username = message['user']
            if username in users:
                username = users[username]
            else:
                print(f"[WARNING] Failed to map uid to slack username - name will remain the unmapped uid: {username}")
        else:
            print(f"[ERROR] No 'user' field in message - defaulting to '<unknown user>'")
    return username


def parse_text(message, username):
    text = message.get('text')
    if text:
        timestamp = parse_timestamp(message)
        return f"**{username}** *({timestamp})*\n{text}"
    return None


def parse_files(message):
    files = []
    for file in message["files"]:
        if "url_private" in file:
            file = {
                "colour": None,
                "title": file["title"],
                "type": file["mimetype"].split('/')[0],
                "url": file["url_private"],
                "description": None,
                "timestamp": datetime.fromtimestamp(file["timestamp"]),
            }
            files.append({k:v for k,v in file.items() if v is not None})
            print(f"[INFO] Attached file: {file['title']}")
        else:
            print(f"[ERROR] File has no 'url_private' field - Unable to migrate file: {file}")
    files = [discord.Embed(**f) for f in files]
    files = [e.set_image(url=e.url) for e in files]
    
    if not "user" in message:
        print(f"[DEBUG] files can exist without a 'user' field!!!")
    
    return files


def parse_message(message, users):
    msg = None
    files = None

    if message.get("subtype", None) == "channel_join":
        print(f"[INFO] Message is a 'channel_join' message")
        return None

    if message.get("subtype", None) == "bot_message":
        print(f"[INFO] Message is a 'bot_message' message")
        return None
    
    msg_id = message.get("client_msg_id", None)
    username = parse_user(message, users)
    
    if "text" in message:
        msg = parse_text(message, username)
    
    if "files" in message:
        files = parse_files(message)

    # Create message-header for pure attachments
    if files and not msg:
        timestamp = parse_timestamp(message)
        
        msg = f"**{username}** *({timestamp})* - *Attachments:*"
    
    if not msg and not files:
        print(f"[ERROR] Failed to parse message: {message}")
        return None

    thread = message.get("thread_ts", None)

    return msg_id, msg, files, thread


async def send_message(ctx, msg, ref=None, embeds=None, allowed_mentions=None):
    if not msg:
        print(f"[DEBUG] Why are you here? - Skipping empty message")
        return None
    
    first_ref = None
    last_ref = None
    # Split and send message *until* the remainder is within the limit, with references
    bot_prefix = "*continuation:*\n"
    while len(msg) > MAX_CHARACTERS:
        ref = await ctx.send(msg[:MAX_CHARACTERS], reference=ref, allowed_mentions = allowed_mentions)
        first_ref = first_ref or ref
        msg = bot_prefix+msg[MAX_CHARACTERS:] # tail
        if THROTTLE:
            time.sleep(THROTTLE_TIME_SECONDS)

    # Send the remainder, with any embeds attached
    if not embeds:
        ref = await ctx.send(msg, reference=ref, allowed_mentions = allowed_mentions)
        first_ref = first_ref or ref
        if THROTTLE:
            time.sleep(THROTTLE_TIME_SECONDS)
    else:
        if len(embeds) > MAX_EMBEDS:
            print(f"[INFO] Message contains over {MAX_EMBEDS} embeds.")
            print(f"       They will be split into multiple messages,")
            print(f"        referencing their parent.")

        if discord.__version__[0] >= "2":
            while embeds:
                ref = await ctx.send(msg, embeds=embeds[:MAX_EMBEDS], reference=last_ref or ref, allowed_mentions = allowed_mentions)
                first_ref = first_ref or ref
                last_ref = last_ref or ref
                if THROTTLE:
                    time.sleep(THROTTLE_TIME_SECONDS)
                msg = "*Additional attachments:*"
                embeds=embeds[MAX_EMBEDS:] # tail
        else:
            for embed in embeds:
                ref = await ctx.send(msg, embed=embed, reference=last_ref or ref, allowed_mentions = allowed_mentions)
                first_ref = first_ref or ref
                last_ref = last_ref or ref
                if THROTTLE:
                    time.sleep(THROTTLE_TIME_SECONDS)
                msg = "*Additional attachments:*"

    return first_ref


async def import_files(ctx, fs, users, slack2discord_users, channels):
    # # dict mapping slack msg-id -> discord message for migrating replies.
    # # Appears slack does not have replies, so this dict is useless.
    # messages = {}
    # dict mapping slack thread_timestamp -> discord thread
    #  If discord.py < 2.0 this is instead used to reference thread-owner
    threads = {}
    for json_file in sorted(fs):
        print(f"[INFO] Parsing file: {json_file}")
        try:
            with open(json_file, encoding="utf-8") as f:
                for message in json.load(f):
                    print(f"[INFO] Parsing message:")
                    parsed = parse_message(message, users)
                    if parsed:
                        msg_id, msg, files, thread_ts = parsed

                        if msg:
                            context = ctx
                            thread_owner = None
                            if not msg_id:
                                print(f"[WARNING] No message-id found - will be unlinkable")
                            msg = await fill_references(ctx, msg, users, slack2discord_users, channels)
                            print(f"[INFO] Importing message: '{msg}'")
                            if thread_ts:
                                # Prefix to clarify message owns/belongs to thread
                                prefix = "[Thread OP] "
                                if thread_ts in threads:
                                    print(f"[INFO] Message belongs to thread: {thread_ts}")
                                    if discord.__version__[0] < "2":
                                        # Emulating threads by converting it into a reply-chain
                                        thread_owner = threads[thread_ts]
                                        prefix = "[Thread] "
                                    else:
                                        context = threads[thread_ts]
                                if discord.__version__[0] < "2":
                                    msg = prefix + msg


                            disable_notifications = discord.AllowedMentions.none()
                            message = await send_message(context, msg, ref=thread_owner, embeds=files if files else None, allowed_mentions = disable_notifications)
                            # messages[msg_id] = message

                            if thread_ts:
                                if not thread_ts in threads:
                                    print(f"[INFO] Message owns a thread: {thread_ts}")
                                    if discord.__version__[0] < "2":
                                        print(f"       Contents will be sent directly to text-channel, referencing this, instead")
                                        threads[thread_ts] = message
                                    else:
                                        print(f"       Creating thread")
                                        threads[thread_ts] = await message.create_thread(name=thread_ts, reason="Migrating Slack thread")
                                if discord.__version__[0] >= "2":
                                    # Threads need to be archived after each message, as well as creation.
                                    await threads[thread_ts].edit(archived=True)
                            print(f"[INFO] Message imported!")

                        if not msg and not files:
                            print(f"[ERROR] skipping message - Found neither text nor files in message: {message}")
                    else:
                        print(f"[INFO] Ignored unparsed message.")
                    print(f"") # empty line
        except OSError as e:
            print(f"[ERROR] {e}")
        print(f"") # extra empty line
    # return messages

async def import_slack_directory(ctx, path, slack_dir, match_channel=True):
    if not ctx:
        print(f"[ERROR] Import aborted - No context was given!")
    if not slack_dir:
        print(f"[ERROR] Import aborted - Failed to parse any slack-log directory at {path}")
    elif not slack_dir["history"]:
        print(f"[ERROR] Import aborted - No .json files found at {path}")
    else:
        if match_channel == True:
            print(f"[INFO] Creating missing channels to facilitate channel-references")
            for ch in slack_dir["history"]:
                print(f"[INFO] Checking channel: {ch}")
                await get_or_create_channel(ctx, ch)

        print(f"[INFO] Importing channels")
        users, slack2discord_users, channels = parse_important_files(slack_dir)
        for ch, fs in slack_dir["history"].items():
            print(f"[INFO] Importing channel: {ch}")
            if match_channel == True:
                ctx = await get_or_create_channel(ctx, ch)
            await import_files(ctx, fs, users, slack2discord_users, channels)
            print(f"[INFO] Completed importing channel: {ch}")
        print(f"[INFO] Import complete")


def register_commands():
    @bot.command(pass_context=True)
    async def import_all(ctx, *kwpath):
        """
        Attempts to import all slack history from the specified path (relative to the bot).
        The path should be the root of the json data, and not a specific channel.
        Only one path can be supplied, if more than one is given only the first will be used.
        The channels will be derived from the subdirectories corresponding to slack channels.
        Will automatically create channels if they don't exist.
        :param ctx:
        :param path:
        :return:
        """
        paths = list(kwpath)
        path = paths[0]
        print(f"[INFO] Attempting to import '{path}' to server '#{ctx.message.guild.name}'")
        slack_dir = parse_slack_directory(path, force_all=True)
        
        await import_slack_directory(ctx, path, slack_dir)

    @bot.command(pass_context=True)
    async def import_path(ctx, *kwpath):
        """
        Attempts to import the slack history from the .json files at specified path (relative to the bot).
        The path should be the subdirectory corresponding to the desired channel, or exact .json files.
        Will automatically create the channel if it doesn't exist.
        Multiple paths can be passed, in which case the corresponding files will be imported in order.
        Note that this will fail to reference channels that neither exist nor wereincluded in the command
        :param ctx:
        :param path:
        :return:
        """
        paths = list(kwpath)
        
        print(f"[INFO] Attempting to import '{paths}' to server '#{ctx.message.guild.name}'")
        slack_dir = parse_slack_directory(paths[0])
        if not slack_dir:
            print(f"[ERROR] Failed to parse slack directory")
            return

        for path in paths[1:]:
            for k, v in parse_slack_directory(path)["history"].items():
                slack_dir["history"][k] = slack_dir["history"].get(k,[]) + v
            
        await import_slack_directory(ctx, slack_dir["root"], slack_dir)

    @bot.command(pass_context=True)
    async def import_here(ctx, *kwpath):
        """
        Attempts to import .json files from the specified path (relative to the bot) to the channel from which the command is invoked.
        Multiple paths can be passed, in which case the corresponding files will be imported in order.
        Note that this will fail to reference channels that doesn't exist
        :param ctx:
        :param path:
        :return:
        """
        paths = list(kwpath)
        for path in paths:
            print(f"[INFO] Attempting to import '{path}' to channel '#{ctx.message.channel.name}'")
            slack_dir = parse_slack_directory(path)
            await import_slack_directory(ctx, path, slack_dir, match_channel=False)


if __name__ == "__main__":
    check_optional_dependencies()
    intents = discord.Intents.default()
    intents.members = True
    if discord.__version__[0] >= "2":
        intents.message_content = True
    bot = commands.Bot(command_prefix="!", intents=intents)
    register_commands()
    bot.run(input("Enter bot token: "))
