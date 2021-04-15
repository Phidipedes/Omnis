import discord
from discord.ext import commands, tasks

import asyncio
import json
import requests
import datetime
import os

from database import memberCollection, trialsCollection #pylint: disable = import-error

class members(commands.Cog, name = "Member Updates"):

    def __init__(self, bot):

        self.bot = bot
        self.updateMembers.start() #pylint: disable=no-member

    @tasks.loop(minutes = 3)
    async def updateMembers(self):

        memberLogChannel = self.bot.get_channel(int(os.getenv("MEMBER_LOG_CHANNEL_ID")))

        hypixelData = requests.get(f"https://api.hypixel.net/guild?key={os.getenv('HYPIXEL_API_KEY')}&name=envision").json()
        cachedData = await memberCollection.find_one({"_id": "envision"})
        trialData = await trialsCollection.find_one({"_id": "envision"})
        trialMembersList = [trial["username"] for trial in trialData["trialMembers"]]

        for member in hypixelData["guild"]["members"]:

            try:

                mojangData = requests.get(f"https://api.ashcon.app/mojang/v2/user/{member['uuid']}").json()

                currentUsername = mojangData["username"].casefold()
                currentRank = member["rank"]

                member["expHistory"]["total"] = sum(member["expHistory"].values())

                if member["uuid"] not in cachedData["members"].keys():

                    await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}": {"username": currentUsername, "rank": member["rank"], "joined": member["joined"], "gexp": member["expHistory"], }}})

                    memberJoinEmbed = discord.Embed(title = f"Member Joined", description = f"UUID: {member['uuid']}\nIGN: {currentUsername}\nJoined at:{member['joined']}", color = discord.Color.green(), timestamp = datetime.datetime.utcnow())
                    await memberLogChannel.send(embed = memberJoinEmbed)

                else:

                    cachedUsername = cachedData["members"][member["uuid"]]["username"]
                    cachedRank = cachedData["members"][member["uuid"]]["rank"]

                    if cachedUsername!= currentUsername:

                        await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.username": currentUsername}})
                        memberUsernameChangeEmbed = discord.Embed(title = f"Member Username Changed", description = f"UUID:{member['uuid']}\n{cachedUsername} **-->** {currentUsername}\nRank: {currentRank}", color = discord.Color.blue(), timestamp = datetime.datetime.utcnow())
                        await memberLogChannel.send(embed = memberUsernameChangeEmbed)

                        if cachedUsername in trialMembersList:

                            trialsCollection.update_one({"_id": "envision", "trialMembers.username": cachedUsername}, {"$set": {"trialMembers.$.username": currentUsername}})

                    if cachedRank != currentRank:

                        await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.rank": currentRank}})
                        memberRankChangeEmbed = discord.Embed(title = f"Member Rank Changed", description = f"UUID: {member['uuid']}\nUsername:{currentUsername}\n{cachedRank} **-->** {currentRank}", color = discord.Color.blue(), timestamp = datetime.datetime.utcnow())
                        await memberLogChannel.send(embed = memberRankChangeEmbed)

                await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.gexp": member["expHistory"]}})

            except:

                me = self.bot.get_user(693132768510607400)

                me.send(f"Check log. SOmethign went wrong")

                print(f"Something went wrong with the following data:\nHypixel Data:\n{member}")
                print(f"Mojang Data:\n{mojangData}")
                print(f"Cached Data:\n{cachedUsername}, {cachedRank}")

                continue

        uuidsLeft = []

        for uuid in cachedData["members"].keys():

            if uuid not in [member["uuid"] for member in hypixelData["guild"]["members"]]:

                uuidsLeft.append(uuid)

        for uuid in uuidsLeft:

            removed = cachedData["members"].pop(uuid)

            memberLeftEmbed = discord.Embed(title = f"Member Left", description = f"UUID: {uuid}\nUsername: {removed['username']}\nRank: {removed['rank']}", color = discord.Color.red(), timestamp = datetime.datetime.utcnow())
            await memberLogChannel.send(embed = memberLeftEmbed)

            if cachedUsername in trialMembersList:

                trialsCollection.update_one({"_id": "envision"}, {"$pull": {"trialMembers": {"username": removed['username']}}})

        if len(uuidsLeft) > 0:

            await memberCollection.update_one({"_id": "envision"}, {"$set": {"members": cachedData["members"]}})

    @updateMembers.before_loop
    async def beforeUpdateMembers(self):

        await self.bot.wait_until_ready()
        await asyncio.sleep(150)

def setup(bot):

    bot.add_cog(members(bot))