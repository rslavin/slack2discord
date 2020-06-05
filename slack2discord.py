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
        json_file_paths = get_file_paths(path)

        if not json_file_paths:
            print(f"[FAILED] No .json files found at {path}")
        else:
            for json_file in sorted(json_file_paths):
                print(f"[INFO] Parsing file: {json_file}")
                try:
                    with open(json_file) as f:
                        for message in json.load(f):
                            if all(key in message for key in ['user_profile', 'ts', 'text']):
                                username = (message['user_profile']['real_name'])
                                timestamp = datetime.fromtimestamp(float(message['ts'])).strftime(
                                    '%m/%d/%Y at %H:%M:%S')
                                text = (message['text'])
                                msg = f"**{username}** *({timestamp})*\n{text}"
                                await ctx.send(msg)
                                print(f"[INFO] Imported message: '{msg}'")
                                time.sleep(THROTTLE_TIME_SECONDS)
                            else:
                                print("[ERROR] user information, timestamp, or message text missing")
                except Exception as e:
                    print(f"[ERROR] {e}")


if __name__ == "__main__":
    bot = commands.Bot(command_prefix="!")
    register_commands()
    bot.run(input("Enter bot token: "))
