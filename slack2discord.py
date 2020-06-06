#!/usr/bin/env python3
# Author: Rocky Slavin
# Slack message history importer for Discord
import json
import os
import time
from datetime import datetime
from discord.ext import commands

THROTTLE_TIME_SECONDS = 1


def get_file_paths(file_path):
    """
    Returns a list of json files (either the path itself or nested files if the path is a directory).
    :param file_path: String path to directory or file
    :return: List of corresponding .json files
    """
    json_files = []

    # if directory, load files
    if os.path.isdir(file_path):
        json_files = [os.path.join(file_path, f) for f in os.listdir(file_path) if f.endswith(".json")]
    elif file_path.endswith(".json"):
        json_files.append(file_path)

    if not json_files:
        print(f"[ERROR] No .json files found at {file_path}")
    else:
        print(f"[INFO] {len(json_files)} .json files loaded")

    return json_files


def get_display_names(file_path):
    """
    Generates a dictionary of user_id => display_name pairs
    :param file_path: Path to users.json
    :return: Dictionary
    """
    users = {}
    try:
        with open(file_path) as f:
            users_json = json.load(f)
            for user in users_json:
                users[user['id']] = (user['profile']['display_name'] if user['profile']['display_name'] else "UNKNOWN")
                print(f"\tUser ID: {user['id']} -> Display Name: {users[user['id']]}")
    except Exception as e:
        print(f"[ERROR] Unable to load display names: {e}")
        return None
    return users


def fill_mentions(message, users):
    """
    Fills in @mentions with their known display names
    :param message:
    :param users:
    :return:
    """
    for uid, name in users.items():
        message = message.replace(f"<@{uid}>", f"@{name}")
    return message


def register_commands():
    @bot.command(pass_context=True)
    async def import_here(ctx, *path):
        """
        Attempts to import .json files from the specified path (relative to the bot) to the channel from which the
        command is invoked.
        :param ctx:
        :param path:
        :return:
        """
        path = ' '.join(path)
        print(f"[INFO] Attempting to import '{path}' to channel '#{ctx.message.channel.name}'")
        json_file_paths = get_file_paths(path)

        if not json_file_paths:
            print(f"[ERROR] No .json files found at {path}")
        else:
            # attempt to find users.json to fill in @mentions
            user_file_path_dir = os.path.join(os.path.dirname(json_file_paths[0]), "users.json")
            user_file_path_files = os.path.join(os.path.dirname(os.path.dirname(json_file_paths[0])), "users.json")
            users = {}
            print(f"[INFO] Attempting to load users.json")
            if os.path.isfile(user_file_path_dir):
                users = get_display_names(user_file_path_dir)
            elif os.path.isfile(user_file_path_files):
                users = get_display_names(user_file_path_files)
            if users:
                print(f"[INFO] users.json found - attempting to fill @mentions")
            else:
                print(f"[WARNING] No users.json found - @mentions will contain user IDs instead of display names")

            for json_file in sorted(json_file_paths):
                print(f"[INFO] Parsing file: {json_file}")
                try:
                    with open(json_file) as f:
                        for message in json.load(f):
                            if all(key in message for key in ['user_profile', 'ts', 'text']):
                                username = (message['user_profile']['display_name'])
                                timestamp = datetime.fromtimestamp(float(message['ts'])).strftime(
                                    '%m/%d/%Y at %H:%M:%S')
                                text = fill_mentions(message['text'], users)
                                msg = f"**{username}** *({timestamp})*\n{text}"
                                await ctx.send(msg)
                                print(f"[INFO] Imported message: '{msg}'")
                                time.sleep(THROTTLE_TIME_SECONDS)
                            else:
                                print("[WARNING] User information, timestamp, or message text missing")
                except Exception as e:
                    print(f"[ERROR] {e}")
            print(f"[INFO] Import complete")


if __name__ == "__main__":
    bot = commands.Bot(command_prefix="!")
    register_commands()
    bot.run(input("Enter bot token: "))
