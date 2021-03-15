import discord
from discord.ext import commands

import dotenv

import os

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix = "o!", intents = intents, case_insensitive = True)

@bot.event
async def on_ready():

    print("ready")

@bot.command()
async def ping(ctx):

    await ctx.channel.send(f"Pong!")

#loads bot cogs
for extension in os.listdir('./extensions'):

    if extension.endswith(".py"):

        bot.load_extension(F"extensions.{extension[:-3]}")

bot.run(os.getenv("BOT_TOKEN"))