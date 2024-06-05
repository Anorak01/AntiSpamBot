""" Simple discord bot that kicks users that were hacked (usually) """

import discord
import config

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

TOKEN = config.token
MIN_CHANNEL_LIMIT = config.min_channel_limit
DELETE_LIMIT = config.delete_limit
ACTION = config.action

REPORT_CHANNEL_ID = config.report_channel_id

messages: dict[str: dict[str: str]] = {}
"""
messages = {
    "username": {
        "channel": "message"
        "channel2": "message"
    }
}
"""

@client.event
async def on_ready():
    """ Triggered when the bot is ready """
    print(f'Logged in as {client.user}')

@client.event
async def on_message(message: discord.Message):
    """ Triggered on every message """
    if message.author == client.user:
        return

    await process_message(message)

async def process_message(message: discord.Message):
    """ Function that processes the message and acts on it as needed """
    # if user not in messages
    if message.author.name not in messages:
        messages[message.author.name] = {} # add him

    # if channel not in users messages
    if message.channel.id not in messages[message.author.name]:
        messages[message.author.name][message.channel.id] = [] # add it

    # if its a different new message, update it
    if messages[message.author.name][message.channel.id] != message.content:
        messages[message.author.name][message.channel.id] = message.content

    # check if theres enough messages to kick someone
    num_of_same_messages = 0
    for channel in messages[message.author.name]:
        if messages[message.author.name][channel] == message.content:
            num_of_same_messages += 1

    if num_of_same_messages >= MIN_CHANNEL_LIMIT:
        await nuke_user_messages(message, message.author)

async def report_action(message: discord.Message):
    """ Function that reports an action """
    if REPORT_CHANNEL_ID == "":
        print("No report channel id set")
    else:
        print("Reporting action", message.author.name)
        channel = client.get_channel(REPORT_CHANNEL_ID)
        await channel.send(f"Action: {ACTION} on User: {message.author.name}")

async def nuke_user_messages(del_message: discord.Message, user):
    if ACTION == "none":
        print("User has not been nuked, only messages deleted", del_message.author.name)
    elif ACTION == "kick":
        print("Kicking user", del_message.author.name)
        await del_message.guild.kick(user)
    elif ACTION == "ban":
        print("Banning user", del_message.author.name)
        await del_message.guild.ban(user)
    else:
        print("Unknown action, user not nuked, only messages deleted", del_message.author.name)
    await report_action(del_message)
    for channel in del_message.guild.text_channels:
        try:
            async for message in channel.history(limit=DELETE_LIMIT):
                if message.author == user and del_message.content == message.content:
                    try:
                        await message.delete()
                    except discord.Forbidden:
                        print("Couldn't access channel, forbidden")
        except discord.Forbidden:
            print("Couldn't access channel, forbidden")

client.run(TOKEN)