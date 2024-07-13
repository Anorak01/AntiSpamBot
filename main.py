""" Simple discord bot that kicks users that were hacked (usually) """

# TODO: Refactor settings access to output dict instead of str that has to be json dumped - maybe do some fancy stuff with auto defaults?
# TODO: Make a function for setting default settings values if they're not present

import json

import discord
import config

from settingsdb import SettingsDB

from typing import Dict

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Bot(intents=intents)

TOKEN = config.token
DELETE_LIMIT = config.delete_limit

messages: Dict[int, Dict[str, Dict[int, str]]] = {}
"""
messages = {
    guild_id:{
        "username": {
            "channel": "message"
            "channel2": "message"
        }
    }
}
"""

settingsdb = SettingsDB()

settings = discord.SlashCommandGroup("settings", "Settings for the bot")
settings.default_member_permissions = discord.Permissions(administrator=True)

@bot.slash_command(description="Help command")
async def help(ctx: discord.ApplicationContext):
    """ Help command """
    await ctx.respond(embed=HelpEmbed(), view=HelpView(), ephemeral=True)

class HelpView(discord.ui.View):
    """ Help View containing the button to switch to Settings submenu """
    @discord.ui.button(label="Settings", style=discord.ButtonStyle.primary)
    async def button_callback(self, _: discord.Button, interaction: discord.Interaction):
        """ Function called when user presses button """
        await interaction.response.defer()
        await interaction.edit_original_response(embed=SettingsHelpEmbed(), view=SettingsHelpView())

class HelpEmbed(discord.Embed):
    """ Embed for help message"""
    def __init__(self):
        super().__init__(title="Welcome to AntiSpamBot", description="A simple discord bot that monitors channels for those pesky link spamming users", color=discord.Color.blue())
        self.add_field(name="Commands", value="/help - Shows this message\n/settings - Shows/changes the bots settings", inline=False)

class SettingsHelpView(discord.ui.View):
    """ View containing the button to switch back to Help menu """
    @discord.ui.button(label="Back", style=discord.ButtonStyle.primary)
    async def button_callback(self, _: discord.Button, interaction: discord.Interaction):
        """ Function called when user presses button """
        await interaction.response.defer()
        await interaction.edit_original_response(embed=HelpEmbed(), view=HelpView())

class SettingsHelpEmbed(discord.Embed):
    """ Embed for settings message """
    def __init__(self):
        super().__init__(title="Settings", description="Summary of settings that can be changed for the bot with the `/settings <subcommand>` command", color=discord.Color.blue())
        self.add_field(name="Show ```show```", value="Shows the current settings", inline=False)
        self.add_field(name="Action ```action```", value="Action to take on users\n`Default: Kick`", inline=False)
        self.add_field(name="Report Channel ```report_channel```", value="Channel to report to\n`Optional`", inline=False)
        self.add_field(name="Minimum Channel Limit ```channel_limit```", value="How many different channels need to have the same message before the user gets acted upon\n`Default: 5`", inline=False)

class SettingsShowEmbed(discord.Embed):
    """
    Embed that constructs the settings show embed
    Accepts settings as a dict
    """
    def __init__(self, settingsdict: dict): # TODO: Refactor after better default settings are added
        super().__init__(title="Settings", description="Your server settings:", color=discord.Color.blue())
        self.add_field(name="Action", value=settingsdict.get("action", "Kick").capitalize(), inline=False)
        if settingsdict.get("report_channel_id", "None") == "None":
            self.add_field(name="Report Channel", value="None", inline=False)
        else:
            self.add_field(name="Report Channel", value=f"<#{settingsdict.get('report_channel_id', 'None')}>", inline=False)
        self.add_field(name="Minimum Channel Limit", value=settingsdict.get("min_channel_limit", "5"), inline=False)

@settings.command()
async def show(ctx: discord.ApplicationContext):
    """ Command for showing the settings """
    sett = settingsdb.get_settings(ctx.guild.id)
    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    await ctx.respond(embed=SettingsShowEmbed(sett), ephemeral=True)

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
    await ctx.respond(f"Report channel set to {channel.mention}", ephemeral=True)

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
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.streaming, name="loading"))
    await bot.sync_commands()
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="spam"))

    print(f'Logged in as {bot.user}')

@bot.event
async def on_message(message: discord.Message):
    """ Triggered on every message """
    if message.author == bot.user:
        return

    if message.channel.type == discord.ChannelType.private:
        return

    if message.guild != None:
        await process_message(message, message.guild)

async def process_message(message: discord.Message, guild: discord.Guild):
    """ Function that processes the message and acts on it as needed """
    # if user not in messages
    if guild.id not in messages:
        messages[guild.id] = {} # add it

    # if user not in messages
    if message.author.name not in messages[guild.id]:
        messages[guild.id][message.author.name] = {} # add him

    # if channel not in users messages
    if message.channel.id not in messages[guild.id][message.author.name]:
        messages[guild.id][message.author.name][message.channel.id] = "" # add it

    # if its a different new message, update it
    if messages[guild.id][message.author.name][message.channel.id] != message.content:
        messages[guild.id][message.author.name][message.channel.id] = message.content

    # check if theres enough messages to kick someone
    num_of_same_messages = 0
    for channel in messages[guild.id][message.author.name]:
        if messages[guild.id][message.author.name][channel] == message.content:
            num_of_same_messages += 1

    sett = settingsdb.get_settings(guild.id)

    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    min_channel_limit = sett.get("min_channel_limit", "nonce")

    if min_channel_limit == "nonce":
        min_channel_limit = 5

        sett["min_channel_limit"] = 5 # if not set, set to default
        settingsdb.set_settings(guild.id, json.dumps(sett))

    if num_of_same_messages >= min_channel_limit:
        await nuke_user_messages(message, message.author, guild)
        messages[guild.id][message.author.name] = {} # reset messages from that user

async def report_action(message: discord.Message):
    """ Function that reports an action """
    if message.guild != None:
        sett = settingsdb.get_settings(message.guild.id)
    else:
        sett = None

    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    report_channel_id = sett.get("report_channel_id", "nonce")
    act = sett.get("action", "nonce")
    if act == "nonce":
        act = "kick"

        sett["action"] = "kick"
        if message.guild != None:
            settingsdb.set_settings(message.guild.id, json.dumps(sett))

    if report_channel_id == "nonce":
        print("No report channel id set")
    else:
        print("Reporting action", message.author.name)
        try:
            channel = bot.get_channel(report_channel_id)
        except Exception:
            print("Failed to send report")

async def nuke_user_messages(del_message: discord.Message, user: discord.User | discord.Member, guild: discord.Guild):
    """ Function used to nuke user and his bad message """
    sett = settingsdb.get_settings(guild.id)
    if sett is None:
        sett = {}
    else:
        sett = json.loads(sett)

    act = sett.get("action", "nonce")

    if act == "nonce":
        act = "kick"

        sett["action"] = "kick"
        settingsdb.set_settings(guild.id, json.dumps(sett))

    if act == "none":
        print("User has not been nuked, only messages deleted", del_message.author.name)
    elif act == "kick":
        print("Kicking user", del_message.author.name)
        try:
            await guild.kick(user)
        except discord.Forbidden:
            print("Couldn't kick user, forbidden")
    elif act == "ban":
        print("Banning user", del_message.author.name)
        try:
            await guild.ban(user)
        except discord.Forbidden:
            print("Couldn't ban user, forbidden")
    else:
        print("Unknown action, user not nuked, only messages deleted", del_message.author.name)
    await report_action(del_message)
    for channel in guild.text_channels:
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
