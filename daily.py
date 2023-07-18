from datetime import datetime
from math import floor
from utils import getSubstr
import gd
import interactions
from async_lru import alru_cache
from typing import Union

dailyAcceptButton = interactions.Button(style=interactions.ButtonStyle.SUCCESS, label="Accept", custom_id="daily_acceptsub")
dailyRejectButton = interactions.Button(style=interactions.ButtonStyle.DANGER, label="Reject", custom_id="daily_rejectsub")

blobstarID = 1125583545268711435
notifyRoleID = 1125586421252632606

cli = gd.Client()

@alru_cache(maxsize=256)
async def isFridayDaily(i: int) -> bool:
    return ((i - 1080) % 7) == 0

async def isFriday():
    return datetime.now().weekday() == 4

@alru_cache(maxsize=512) # cache limit should be enough
async def levelDetails(levelID: int) -> tuple[str, str]:
    level = await cli.get_level(level_id=levelID)
    return level.name, level.creator.name

async def getDailyDetails(msg: str, client: interactions.Client, token: str, getUser: bool = True) \
        -> Union[tuple[str, str, Union[bool, int], interactions.User], tuple[str, str, Union[bool, int]]]:
    doubleDaily: Union[bool, int] = False
    lines = msg.split("\n")
    dailynum = await getSubstr(lines[0], "y #", " S")
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

async def getDaily():
    # will be implemented later...
    # psuedo-code: 1. go to mongodb table with dailies, query daily
    #              2. return properties in dict
    ...
dailyCalcDict: dict[str, dict[str, Union[datetime, int]]] = {"daily": {"date": datetime(2023, 6, 23), "offset": 1094, "divSeconds": 86400},
                                                             "weekly": {"date": datetime(2023, 7, 2), "offset": 158, "divSeconds": 604800},
                                                             "monthly": {"sum": 24283, "offset": 37}}
async def calcCurrDaily(dType: str = "daily"):
    calcDict = dailyCalcDict[dType]
    dtNow = datetime.now()
    if dType != "monthly":
        diff = (dtNow - calcDict['date']).total_seconds() / calcDict['divSeconds']
        return floor(diff) + calcDict['offset']
    else:
        return round(((dtNow.month + dtNow.year * 12) - calcDict['sum']) / 12) + calcDict['offset']

async def fixEmbedVideo(s: str):
    fixed = s.replace("cdn.discordapp.com", "media.discordapp.net")
    return fixed

async def postDaily(channel: interactions.Channel, dailyID: int, currDaily: int, coolStars: int):
    levelName, levelCreator = await levelDetails(dailyID)
    dt = datetime.now()
    date = f"{('0' + str(dt.month)) if dt.month < 10 else dt.month}/{('0' + str(dt.day)) if dt.day < 10 else dt.day}/{str(dt.year)[2:]}"

    msg = f"__**Daily Challenge - {date} (#{currDaily})**__ <@{notifyRoleID}>"
    msg += f"\n**{levelName}** by **{levelCreator}**"
    msg += f"\nRating: {coolStars} <:blobstar:{blobstarID}>"
    msg += f"\n`{dailyID}`"

    await channel.send(content=msg)
