import discord
from discord.ext import commands, tasks

import asyncio
import json
import requests
import datetime
import os
import pprint

from database import memberCollection, trialsCollection, activityCollection #pylint: disable = import-error
from timezones import eastern #pylint: disable = import-error

class members(commands.Cog, name = "Member Updates"):

    def __init__(self, bot):

        self.bot = bot
        self.updateMembers.start() #pylint: disable=no-member

    @tasks.loop(minutes = 1)
    async def updateMembers(self):

        memberLogChannel = self.bot.get_channel(int(os.getenv("MEMBER_LOG_CHANNEL_ID")))
        trialDateChannel = self.bot.get_channel(int(os.getenv("TRIAL_MEMBER_DATE_CHANNEL_ID")))

        try:
            
            hypixelData = requests.get(f"https://api.hypixel.net/guild?key={os.getenv('HYPIXEL_API_KEY')}&name=envision").json()

        except:

            print(f"Hypixel request failed. This is likely due to server lag causing bad gateway error. ")
            
            pass

        cachedData = await memberCollection.find_one({"_id": "envision"})
        trialData = await trialsCollection.find_one({"_id": "envision"})
        activityData = await activityCollection.find_one({"_id": "envision"})
        trialMembersList = [trial["username"] for trial in trialData["trialMembers"]]
        whitelistedMembersList = [wlmember["username"] for wlmember in activityData["whitelist"]]

        print(hypixelData)

        for member in hypixelData["guild"]["members"]:

            try:

                mojangData = requests.get(f"https://api.ashcon.app/mojang/v2/user/{member['uuid']}").json()

                currentUsername = mojangData["username"].casefold()
                currentRank = member["rank"]

                member["expHistory"]["total"] = sum(member["expHistory"].values())

                if member["uuid"] not in cachedData["members"].keys():

                    await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}": {"username": currentUsername, "rank": member["rank"], "joined": member["joined"], "gexp": member["expHistory"], }}})
                    await memberLogChannel.send(f"<:join:835598873678315550> **{currentUsername}** joined the guild. **|** UUID: {member['uuid']}")

                    memberDate = datetime.datetime.now().astimezone(eastern).replace(hour = 0, minute = 0, second = 0, microsecond = 0) + datetime.timedelta(days = trialData["trialDuration"])

                    await trialsCollection.update_one({"_id": "envision"}, {"$push": {"trialMembers": {"username": currentUsername, "memberDate": memberDate}}})
                    await trialDateChannel.send(f"<:added:835599921113202688> **{currentUsername}** added to trial members on **{datetime.datetime.now().astimezone(eastern).date().strftime('%m/%d/%Y')}** (Member on **{memberDate.date().strftime('%d/%m/%Y')}**) **|** Added automatically on member join")

                else:

                    cachedUsername = cachedData["members"][member["uuid"]]["username"]
                    cachedRank = cachedData["members"][member["uuid"]]["rank"]

                    if cachedUsername!= currentUsername:

                        await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.username": currentUsername}})
                        await memberLogChannel.send(f"<:update:835597734177538078> **{cachedUsername}** username changed **|** {cachedUsername} -> **{currentUsername}** **|** UUID: {member['uuid']} **|** Rank: {currentRank}")

                        if cachedUsername in trialMembersList:

                            await trialsCollection.update_one({"_id": "envision", "trialMembers.username": cachedUsername}, {"$set": {"trialMembers.$.username": currentUsername}})

                        if cachedUsername in whitelistedMembersList:

                            await activityData.update_one({"_id": "envision", "whitelist.username": cachedUsername}, {"$set": {"whitelist.$.username": currentUsername}})

                    if cachedRank != currentRank:

                        await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.rank": currentRank}})
                        await memberLogChannel.send(f"<:update:835597734177538078> **{currentUsername}** rank changed **|** {cachedRank} -> **{currentRank}** **|** UUID: {member['uuid']}")

                await memberCollection.update_one({"_id": "envision"}, {"$set": {f"members.{member['uuid']}.gexp": member["expHistory"]}})

            except:

                me = self.bot.get_user(693132768510607400)

                await me.send(f"Check log. Something went wrong")

                print(f"Something went wrong with the following data:\nHypixel Data:\n{member}")
                print(f"Mojang Data:\n{mojangData}")
                print(f"Cached Data:\n{cachedUsername}, {cachedRank}")

                continue

        for uuid in cachedData["members"].keys():

            username = cachedData["members"][uuid]["username"]

            if uuid not in [member["uuid"] for member in hypixelData["guild"]["members"]]:

                await memberCollection.update_one({"_id": "envision"}, {"$unset": {f"members.{uuid}": ""}})

                if username in trialMembersList:

                    await trialsCollection.update_one({"_id": "envision"}, {"$pull": {"trialMembers": {"username": username}}})
                    await trialDateChannel.send(f"<:removed:835599920860758037> **{username}** removed from trial members **|** Removed automatically on member leave")

                if username in whitelistedMembersList:

                    await activityCollection.update_one({"_id": "envision"}, {"$pull": {"whitelist": {"username": username}}})

                await memberLogChannel.send(f"<:leave:835598873707282442> **{username}** left the guild **|** UUID: {member['uuid']} **|** Rank: {cachedData['members'][uuid]['rank']}")

    @updateMembers.before_loop
    async def beforeUpdateMembers(self):

        await self.bot.wait_until_ready()
        await asyncio.sleep(150)

def setup(bot):

    bot.add_cog(members(bot))