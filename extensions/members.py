import discord
from discord.ext import commands, tasks

import asyncio
import json
import requests
import datetime
import os

from database import memberCollection #pylint: disable = import-error

class members(commands.Cog, name = "Member Updates"):

    def __init__(self, bot):

        self.bot = bot
        self.updateMembers.start() #pylint: disable=no-member

    @tasks.loop(minutes = 2.5)
    async def updateMembers(self)  :

        memberLogChannel = self.bot.get_channel(int(os.getenv("MEMBER_LOG_CHANNEL_ID")))

        hypixelData = requests.get(f"https://api.hypixel.net/guild?key={os.getenv('HYPIXEL_API_KEY')}&name=envision").json()
        cachedData = await memberCollection.find_one({"_id": "envision"})

        for member in hypixelData["guild"]["members"]:

            mojangData = requests.get(f"https://api.mojang.com/user/profiles/{member['uuid']}/names").json()
            currentUsername = mojangData[-1]["name"].casefold()
            currentRank = member["rank"]

            member["expHistory"]["total"] = sum(member["expHistory"].values())

            if member["uuid"] not in cachedData["members"].keys():

                memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}": {"username": currentUsername, "rank": member["rank"], "joined": member["joined"], "gexp": member["expHistory"], }}})

                memberJoinEmbed = discord.Embed(title = f"Member Joined", description = f"UUID: {member['uuid']}\nIGN: {currentUsername}\nJoined at:{member['joined']}", color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
                await memberLogChannel.send(embed = memberJoinEmbed)

            else:

                cachedUsername = cachedData["members"][member["uuid"]]["username"]
                cachedRank = cachedData["members"][member["uuid"]]["rank"]

                if cachedUsername!= currentUsername:

                    memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.username": currentUsername}})
                    memberUsernameChangeEmbed = discord.Embed(title = f"Member Username Changed", description = f"UUID:{member['uuid']}\n{cachedUsername} **-->** {currentUsername}\nRank: {currentRank}", color = discord.Color.blue(), timestamp = datetime.datetime.utcnow())
                    await memberLogChannel.send(embed = memberUsernameChangeEmbed)

                if cachedRank != currentRank:

                    memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.rank": currentRank}})
                    memberRankChangeEmbed = discord.Embed(title = f"Member Rank Changed", description = f"UUID: {member['uuid']}\nUsername:{currentUsername}\n{cachedRank} **-->** {currentRank}", color = discord.Color.blue(), timestamp = datetime.datetime.utcnow())
                    await memberLogChannel.send(embed = memberRankChangeEmbed)

        uuidsLeft = []

        for uuid in cachedData["members"].keys():

            if uuid not in [member["uuid"] for member in hypixelData["guild"]["members"]]:

                uuidsLeft.append(uuid)

        for uuid in uuidsLeft:

            removed = cachedData["members"].pop(uuid)

            memberLeftEmbed = discord.Embed(title = f"Member Left", description = f"UUID: {uuid}\nUsername: {removed['username']}\nRank: {removed['rank']}", color = discord.Color.red(), timestamp = datetime.datetime.utcnow())
            await memberLogChannel.send(embed = memberLeftEmbed)

        if len(uuidsLeft) > 0:

            memberCollection.update_one({"_id": "envision"}, {"$set": {"members": cachedData["members"]}})

    @updateMembers.before_loop
    async def beforeUpdateMembers(self):

        await self.bot.wait_until_ready()
        await asyncio.sleep(150)

def setup(bot):

    bot.add_cog(members(bot))