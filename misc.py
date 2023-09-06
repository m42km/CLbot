from datetime import datetime, timezone, timedelta
from math import floor, ceil
from embeds import errorEmbed, successEmbed
from req import requestGET
import interactions
from async_lru import alru_cache
import motor.motor_asyncio as motorAsyncIO
import os
from json import load
import json
from gd import Client

f = open("configdiscord.json")
miscConfig = load(f)
f.close()

dailyAcceptButton = interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Accept", custom_id="daily_acceptsub")
dailyRejectButton = interactions.Button(style=interactions.ButtonStyle.DANGER, label="Reject", custom_id="daily_rejectsub")
dailyNotesButton = interactions.Button(style=interactions.ButtonStyle.PRIMARY, label="Add/Set Notes", custom_id="daily_subnotes")

blobstarID = miscConfig['emojis']['blobstar']
notifyRoleID = miscConfig['roles']['notifyEvents']

cli = Client()

mongoURI = os.getenv("MONGO_URI")
mongoClient: motorAsyncIO.AsyncIOMotorClient = motorAsyncIO.AsyncIOMotorClient(mongoURI)
collection = mongoClient

dailybotDB: motorAsyncIO.AsyncIOMotorDatabase = mongoClient['dailybotDB']

dailyChallenges: motorAsyncIO.AsyncIOMotorCollection = dailybotDB['dailyLevels']
dailyChallsLocal: dict = {"daily": {}, "weekly": {}, "monthly": {},
                          "daily1": {}, "daily2": {}}

# https://challengelist.gd/api/v1/players/?after=4&before=6 to get acc id 5

dailyUsers: motorAsyncIO.AsyncIOMotorCollection = dailybotDB['dailyLeaderboard']
listUsers: motorAsyncIO.AsyncIOMotorCollection = dailybotDB['clAccounts']
discList: dict = {}
listDisc: dict = {}
# discord_id: text, account_id: int32
dailyUsersLocal: dict = {}
dailyUsersLeaderboard: list = []
leaderboardIndex: dict = {}
existingDailyUsers: list = []

tz = timezone(timedelta(hours=-5)) # CDT (UTC-5)
tz2 = timezone(timedelta(hours=0))

dailyCalcDict = {"daily": {"date": datetime(2023, 6, 23, tzinfo=tz2), "offset": 1094, "divSeconds": 86400},
                                                             "weekly": {"date": datetime(2023, 7, 2, tzinfo=tz2), "offset": 158, "divSeconds": 604800},
                                                             "monthly": {"sum": 24283, "offset": 37}}

dailyCol = 0xfafa45

@alru_cache(maxsize=1000)
async def getSubstr(s: str, after: str, before: str) -> str:
    return s[s.index(after) + len(after): s.index(before)]

async def dUserExists(discord_id):
    return True if str(discord_id) in existingDailyUsers else False

async def dUpdate(col, exp1, exp2):
    try:
        r = await col.find_one_and_update(exp1, exp2)
    except Exception as e:
        r = await errorEmbed(e)
    return r

async def dFind(col, exp):
    try:
        r = await col.find_one(exp)
    except Exception as e:
        r = await errorEmbed(e)
    return r

async def lLinkAccount(discord_id: str, account_name: str) -> interactions.Embed:
    try:
        await listUsers.insert_one({"discord_id": discord_id, "account_name": account_name})
        discList.update({discord_id: account_name})
        listDisc.update({account_name: discord_id})
        return await successEmbed(f"<@{discord_id}> has been linked to the Challenge List account **{account_name}**")
    except Exception as e:
        return await errorEmbed(e)

async def lUnlinkAccount(discord_id: str) -> interactions.Embed:
    try:
        await listUsers.delete_one({"discord_id": discord_id})
        await listUsersCollect()
        return await successEmbed(f"<@{discord_id}> has been unlinked from their previous Challenge List account.")
    except Exception as e:
        return await errorEmbed(e)

async def dFindUser(discord_id: int):
    if discord_id in dailyUsersLocal.keys():
        return dailyUsersLocal[discord_id]
    else:
        return False

async def addPoints(user_id: int, pts: int, showEmbed: bool = True):
    exists = await dUserExists(user_id)
    if exists:
        r = await dUpdate(dailyUsers, {"discord_id": str(user_id)}, {"$inc": {"points": pts}})
    else:
        r = await dailyUsers.insert_one({"discord_id": str(user_id), "points": pts})

    await dailyLocalCollect()

    if type(r) != interactions.Embed:
        if showEmbed:
            return successEmbed(f"{pts} points added to <@{user_id}>, they now have {r['points']} points")
        else:
            return
    return r

async def getPoints(user_id: int):
    if str(user_id) in existingDailyUsers:
        points, place = dailyUsersLocal[user_id], leaderboardIndex[dailyUsersLocal[user_id]]
        desc = f"<@{user_id}> has **{points}** points and is **#{place}**"
    else:
        desc = f"<@{user_id}> has **0** points"
    embed = interactions.Embed(title="Points", description=desc, color=0x5555FF)
    return embed

async def getPointsInt(user_id: int):
    if str(user_id) in existingDailyUsers:
        return dailyUsersLocal[user_id]
    else:
        return 0

async def setPoints(user_id: int, pts: int):
    exists = await dUserExists(user_id)
    if exists:
        r = await dUpdate(dailyUsers, {"discord_id": str(user_id)}, {"$set": {"points": pts}})
    else:
        r = await dailyUsers.insert_one({"discord_id": str(user_id), "points": pts})

    await dailyLocalCollect()
    if type(r) != interactions.Embed:
        return await successEmbed(f"<@{user_id}>'s points set to {pts}")
    return r

# async def dLeaderboardPos():
#     pLbPipeline = [{'$match': {'points': {'$gte': 50}}}, {'$count': 'discord_id'}]
#     try:
#         ag = await dailyUsers.aggregate(pLbPipeline)
#     except Exception as e:
#         return await errorEmbed(e)
#
#     return ag[0]['discord_id']

@alru_cache(maxsize=500)
async def dLeaderboardDetails(title: str):
    # Leaderboard (#11-20)
    if "Top" in title:
        page = 1
        limit = int(await getSubstr(title, "Top ", ")"))
    else:
        # ex: Daily Leaderboard (#11-20)
        start = int(await getSubstr(title, "#", "-")) # start = 11
        end = int(await getSubstr(title, "-", ")")) # end = 20
        limit = end - start + 1 # limit = 10
        page = ceil((start - 1) / limit) + 1 # page = 2
    return page, limit

@alru_cache(maxsize=500)
async def dLeaderboardTitle(page: int, limit: int):
    after = (page - 1) * limit
    return f"Daily Leaderboard (#{after + 1}-{after + limit})"

@alru_cache(maxsize=500)
async def dLeaderboardButtons(page: int, limit: int):
    backDisabled, nextDisabled = False, False
    after = page * limit
    if after > len(existingDailyUsers):
        nextDisabled = True
    if page == 1:
        backDisabled = True

    backButton = interactions.Button(
        style=interactions.ButtonStyle.SECONDARY, label="Last Page",
        custom_id="dleaderboard_back", disabled=backDisabled
    )
    nextButton = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY, label="Next Page",
        custom_id="dleaderboard_next", disabled=nextDisabled
    )

    return backButton, nextButton

async def dailyLeaderboard(ctx, page: int = 1, limit: int = 10, title: str = None):
    start = ((page - 1) * limit)
    desc, backButton, nextButton = "", None, None
    i = 1
    try:
        for doc in dailyUsersLeaderboard[start:start + limit]:
            desc += f"**#{start + i}:** <@{doc['discord_id']}> - {doc['points']} point{'' if doc['points'] == 1 else 's'}\n"
            i += 1
        suffix = f" (Top {limit})" if page == 1 else f" (#{start + 1}-{start + limit})"
        embed = interactions.Embed(title=("Daily Leaderboard" + suffix) if not title else title, description=desc, color=dailyCol)
        embed.set_footer(text=f"Requested by {ctx.user.username} • ID: {str(ctx.user.id)}",
                         icon_url=ctx.user.avatar_url)
        backButton, nextButton = await dLeaderboardButtons(page, limit)
    except Exception as e:
        embed = await errorEmbed(e)

    return embed, backButton, nextButton

@alru_cache(maxsize=256)
async def isFridayDaily(i: int) -> bool:
    return ((i - 1080) % 7) == 0

async def isFriday():
    return datetime.now().weekday() == 4

@alru_cache(maxsize=512) # cache limit should be enough
async def levelDetails(levelID: int):
    level = await cli.get_level(level_id=levelID)
    return level.name, level.creator.name

async def getDailyDetails(msg: str, client: interactions.Client, token: str, getUser: bool = True):
    doubleDaily = False
    lines = msg.split("\n")
    dailynum = int(await getSubstr(lines[0], "y #", " S"))
    dType = await getSubstr(lines[0], "__", " #")
    if "DDF" in lines[0]:
        # if the completion is for a double daily, return integer specifying which one (either 1 or 2)
        doubleDaily = int(await getSubstr(lines[0], "DDF #", ")"))
    if getUser:
        userID = int(await getSubstr(lines[1], "@", ">"))
        user = await interactions.get(client=client, obj=interactions.User, object_id=userID)
        user._client = interactions.HTTPClient(token)
        return dailynum, dType, doubleDaily, user
    else:
        return dailynum, dType, doubleDaily

async def addDaily(discord_id: str, level_id: str, dtype: str, dailynum: int, stars: int) -> interactions.Embed:
    name, creator = await levelDetails(int(level_id))
    try:
        r = await dailyChallenges.insert_one({"name": name,
                                          "creator": creator,
                                          "discord_id": discord_id,
                                          "level_id": level_id,
                                          "dtype": dtype,
                                          "stars": stars,
                                          "num": dailynum})
        dailyname = dtype.capitalize() if dtype != "daily1" and dtype != "daily2" \
                                       else f"Double Daily Friday {dtype[5]}"
        await dailyLocalCollect()
        return await successEmbed(f'{dailyname} #{dailynum} *{name} by {creator}* added!')
    except Exception as e:
        return await errorEmbed(e)

async def editDaily(dtype: str, dailynum: int, dictReplace: dict):
    r = await dUpdate(dailyChallenges, {"dtype": dtype, "num": dailynum}, {"$set": dictReplace})
    dailyname = dtype.capitalize() if dtype != "daily1" and dtype != "daily2" \
        else f"Double Daily Friday {dtype[5]}"
    if type(r) != interactions.Embed:
        await dailyLocalCollect()
        return await successEmbed(f"{dailyname} #{dailynum} updated!")
    else:
        return r

async def getDailyPoints(dtype: str, dailynum: int):
    if dailynum in dailyChallsLocal[dtype].keys():
        return dailyChallsLocal[dtype][dailynum]['stars']
    return None

async def getDailyInfo(dtype: str, dailynum: int):
    if dailynum in dailyChallsLocal[dtype].keys():
        d = dailyChallsLocal[dtype][dailynum]
        return f"*{d['name']}* by {d['creator']} ( {d['stars']} <:blobstar:{blobstarID}>"
    return "None!"

async def dailyLocalCollect():
    global dailyUsersLeaderboard, existingDailyUsers, dailyChallsLocal, leaderboardIndex
    dailyUsersLeaderboard2, existingDailyUsers2, leaderboardIndex2 = [], [], {}
    i = 1
    dUsersNew = await dailyUsers.aggregate([{'$sort': {'points': -1}}]).to_list(length=None)

    for user in dUsersNew:
        existingDailyUsers2.append(user["discord_id"])
        # these are all for making lookup faster and easier
        dailyUsersLeaderboard2.append({"discord_id": int(user["discord_id"]), "points": user['points']})
        leaderboardIndex2.update({user['points']: i})
        dailyUsersLocal.update({int(user["discord_id"]): user['points']})
        i += 1

    dailyUsersLeaderboard = dailyUsersLeaderboard2
    existingDailyUsers = existingDailyUsers2
    leaderboardIndex = leaderboardIndex2

async def listUsersCollect():
    global discList, listDisc
    lUsersNew = await listUsers.aggregate([{'$sort': {'num': -1}}]).to_list(length=None)
    discList2, listDisc2 = {}, {}

    for user in lUsersNew:
        dID, aID = user['discord_id'], user['account_name']
        discList2.update({dID: aID})
        listDisc2.update({aID: dID})

    discList = discList2
    listDisc = listDisc2

async def dChallsCollect():
    dChallsNew = await dailyChallenges.aggregate([{'$sort': {'num': -1}}]).to_list(length=None)
    for challenge in dChallsNew:
        dailyChallsLocal[challenge['dtype']].update({challenge['num']: challenge})

async def calcCurrDaily(dType: str = "daily") -> int:
    calcDict = dailyCalcDict[dType]
    dtNow = datetime.now(tz)
    if dType != "monthly":
        diff = (dtNow - calcDict['date']).total_seconds() / calcDict['divSeconds']
        return floor(diff) + calcDict['offset']
    else:
        return round(((dtNow.month + dtNow.year * 12) - calcDict['sum']) / 12) + calcDict['offset']

async def fixEmbedVideo(s: str):
    fixed = s.replace("cdn.discordapp.com", "media.discordapp.net")
    return fixed

async def postDaily(channel: interactions.Channel, dtype: str, num: int):
    d = await getDailyPoints(dtype, num)
    dailyID, coolStars = int(d['level_id']), d['stars']
    levelName, levelCreator = await levelDetails(int(d['level_id']))
    dt = datetime.now()
    date = f"{('0' + str(dt.month)) if dt.month < 10 else dt.month}/{('0' + str(dt.day)) if dt.day < 10 else dt.day}/{str(dt.year)[2:]}"
    dailyname = (dtype.capitalize() + " Challenge") if dtype != "daily1" and dtype != "daily2" \
        else f"DOUBLE DAILY FRIDAY {dtype[5]}"

    msg = f"__**{dailyname} - {date} (#{num})**__ <@&{notifyRoleID}>"
    msg += f"\n**{levelName}** by **{levelCreator}**"
    msg += f"\nRating: {coolStars} <:blobstar:{blobstarID}>"
    msg += f"\n`{dailyID}`"

    dMessage = await channel.send(content=msg)
    if dtype == "daily":
        return # don't pin dailies

    pins = await channel.get_pinned_messages()
    await channel.pin_message(dMessage)
    for msg in pins:
        if dailyname in msg.content:
            await channel.unpin_message(msg)
            break

async def discToListUser(discord_id: str):
    if discord_id not in discList.keys():
        return 0
    else:
        return discList[discord_id]

async def listToDisc(account_name: str):
    if account_name not in listDisc.keys():
        return 0
    else:
        return f"{listDisc[account_name]}"

async def discToListPoints(discord_id: str):
    listUsername = await discToListUser(discord_id)
    if listUsername == 0:
        return 0
    else:
        pts = (await requestGET(f"https://challengelist.gd/api/v1/players/ranking/?name_contains={listUsername}"))[0]['scores']
        return pts
