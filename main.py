""" Simple discord bot that kicks users that were hacked (usually) """

import json

import discord
import config

from settingsdb import SettingsDB


intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

TOKEN = config.token
MIN_CHANNEL_LIMIT = config.min_channel_limit
DELETE_LIMIT = config.delete_limit
ACTION = config.action

REPORT_CHANNEL_ID = config.report_channel_id
MY_GUILD = config.guild_id

messages: dict[str: dict[str: str]] = {}
"""
messages = {
    "username": {
        "channel": "message"
        "channel2": "message"
    }
}
"""

settingsdb = SettingsDB()

settings = discord.SlashCommandGroup("settings", "Settings for the bot")
settings.default_member_permissions = discord.Permissions(administrator=True)

@bot.slash_command(description="Help command")
async def help(ctx: discord.ApplicationContext):
    """ Help command """
    await ctx.respond("""All you can do with this bot:
                      /help - Shows this message
                      /settings - Shows the current settings""", ephemeral=True)

@settings.command()
@discord.option("setting", description="Setting to change", choices=[discord.OptionChoice("None", "none"), discord.OptionChoice("Kick", "kick"), discord.OptionChoice("Ban", "ban")], required=True)
async def action(ctx: discord.ApplicationContext,
                 setting: str):
    """ Command for setting the action to take on users """
    sett = settingsdb.get_settings(ctx.guild.id)
    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    sett["action"] = setting

    settingsdb.set_settings(ctx.guild.id, json.dumps(sett))
    await ctx.respond(f"Action set to {setting}", ephemeral=True)

@settings.command()
@discord.option("channel", description="Channel to report to", type=discord.TextChannel, required=True)
async def report_channel(ctx: discord.ApplicationContext,
                         channel: discord.TextChannel):
    """ Command for setting the channel the report is sent to """
    sett = settingsdb.get_settings(ctx.guild.id)

    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    sett["report_channel_id"] = channel.id

    settingsdb.set_settings(ctx.guild.id, json.dumps(sett))
    await ctx.respond(f"Report channel set to {ctx.channel.mention}", ephemeral=True)

@settings.command(description="Set the minimum channel limit for user to get kicked/banned")
@discord.option("limit", description="Minimum channel limit <1, 15>", min_value=1, max_value=15, required=True)
async def channel_limit(ctx: discord.ApplicationContext,
                        limit: int):
    """ Command for setting the minimum channel limit """
    sett = settingsdb.get_settings(ctx.guild.id)

    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    sett["min_channel_limit"] = limit

    settingsdb.set_settings(ctx.guild.id, json.dumps(sett))
    await ctx.respond(f"Minimum channel limit set to {limit}", ephemeral=True)

bot.add_application_command(settings)

@bot.event
async def on_ready():
    """ Triggered when the bot is ready """
    async for guild in bot.fetch_guilds():
        if guild.id != MY_GUILD:
            print(f'Left {guild.name} ({guild.id})')
            await guild.leave()
    await bot.sync_commands()
    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message: discord.Message):
    """ Triggered on every message """
    if message.author == bot.user:
        return

    await process_message(message)

@bot.event
async def on_guild_join(guild: discord.Guild):
    """ Triggered when the bot joins a guild """
    if guild.id != MY_GUILD:
        await guild.leave()
        print(f'Someone tried inviting me to {guild.name} ({guild.id})')

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
        try:
            channel = bot.get_channel(REPORT_CHANNEL_ID)
            await channel.send(f"Action: {ACTION} on User: {message.author.name}")
        except Exception:
            print("Failed to send report")

async def nuke_user_messages(del_message: discord.Message, user):
    """ Function used to nuke user and his bad message """
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

bot.run(TOKEN)
