import functools
import mysql.connector
from mysql.connector import Error
import pymysql
from async_lru import alru_cache
from json import loads as to_json
import requests
import interactions
from autocorrect import *

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}


# INSERT INTO users (`discord_id`, `linked_user`) VALUES (123, "wow")
async def sql_query(connection, query):
    cursor = connection.cursor()
    try:
        r = cursor.execute(query)
        print(r)
        return r
    except Error as e:
        print(f"The error '{e}' occurred")

def create_connection(host_name, user_name, db_name=None, user_password=None) -> mysql.connector.connection_cext.CMySQLConnection:
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name,
            user=user_name,
            passwd=user_password,
            database=db_name
        )
        print("connection worked:")
        print(connection)
    except Error as e:
        print(f"The error '{e}' occurred")

    return connection

@alru_cache(maxsize=150)
async def calcPoints(n): # calculates list points, n is position
    return round(259.688*(0.962695**n), 2) if n < 101 else 0

# https://www.youtube.com/watch?v=wZxRdKi4uuU
@alru_cache(maxsize=150)
async def getVidThumbnail(url): # video URL to thumbnail
    vCode = url.split("=")[1]
    #print("https://img.youtube.com/vi/" + vCode + "0.jpg")
    return "https://img.youtube.com/vi/" + vCode + "/maxresdefault.jpg"

@alru_cache(maxsize=200)
async def remLastChar(s: str):
    l = len(s) - 2
    return s[0:l]

@alru_cache(maxsize=50)
async def getChallenges(limit, after, title):
    r = to_json(
        requests.get(f"https://challengelist.gd/api/v1/demons/?limit={limit}&after={after}", headers=headers).text)
    if not r:
        return None
    embed = interactions.Embed(color=0xffae00, title=title)
    for demon in r:
        #print(demon)
        name, pos, creator, verifier, video = demon['name'], demon['position'], demon['publisher']['name'], \
                                              demon['verifier']['name'], demon['video']
        if name == "Gamma Dan":
            video = "https://www.youtube.com/watch?v=Z5UEKYwj-n4"  # lololol
        points = await calcPoints(pos)
        embed.add_field(name=f"**{pos}. {name}** by **{creator}**",
                        value=f"Verified by **{verifier}** | [**Video**]({video})\n**{points}** points",
                        inline=False)
    embed.set_thumbnail(await getVidThumbnail(r[0]['video']))
    return embed

@alru_cache(maxsize=60)
async def showChallenge(context: interactions.CommandContext, lvl_name: str = None, lvl_pos: int = None, challenge_names: tuple = None):
    if lvl_name:
        cLevel = await correctLevel(context, lvl_name, challenge_names=challenge_names)
        if type(cLevel) == tuple:
            print(cLevel)
            return tuple(cLevel)
        if not cLevel:
            levels = []
        else:
            levels = requests.get(f"https://challengelist.gd/api/v1/demons/?name_contains={cLevel}", headers=headers).json()

        if len(levels) > 1:
            i = 0
            for level in levels:
                if len(level['name']) == level:
                    g_level = levels[i]
                    break
                else:
                    i += 1
            if len(levels) > 1:
                g_level = levels[0]
        elif len(levels) < 1:
            await context.send("**Error:** Couldn't find any levels with that name. Did you misspell it or something?")
            return None
        else:
            g_level = levels[0]
    elif lvl_pos:
        g_level = {"position": lvl_pos}
    f_level = requests.get(f"https://challengelist.gd/api/v1/demons/{g_level['position']}", headers=headers).json()[
        'data']

    position = "#" + str(f_level['position'])
    name = f_level['name']
    creator = f_level['publisher']['name']

    verifier = f_level['verifier']['name']
    fps = f_level['fps'] if f_level['fps'] else "Any"
    list_percent = f_level['requirement']
    verification_video = f_level['video']
    points = await calcPoints(f_level['position']) if f_level['position'] < 101 else "None"
    level_id = f_level['level_id']
    thumbnail = await getVidThumbnail(verification_video)

    l_overview_info = [f"Verified by **{verifier}**",
                       f"**FPS:** {fps}",
                       f"**Verification: [Link]({verification_video})**",
                       f"**ID:** {level_id}",
                       f"**Points Awarded:** {points}"]
    overview_info = "\n".join(l_overview_info)

    victors = []
    full_victors = []
    curr_victors_msg = ""

    vLen = 0
    progress = []
    pLen = 0

    for completion in f_level['records']:
        if completion['status'] != "approved" or completion['player']['banned']:  # skip the record if this happens
            continue

        p_flag = f" :flag_{completion['nationality']['country_code'].lower()}:" if completion[
            'nationality'] else ""
        p_name = completion['player']['name']
        c_progress = completion['progress']

        proof = completion['video']

        if c_progress == 100:
            v_data = f"**[{p_name}]({proof})**{p_flag}"
            if len(v_data) + vLen > 900:
                #print(len(curr_victors_msg))
                curr_victors_msg = await remLastChar(curr_victors_msg)
                full_victors.append(curr_victors_msg)
                curr_victors_msg = v_data + ", "
                vLen = len(v_data)
                continue
            vLen += len(v_data)
            curr_victors_msg += v_data + ", "
    full_victors.append(await remLastChar(curr_victors_msg))
    #print(full_victors)
    embed = interactions.Embed(color=0xffae00, title=f"{position}. {name} by {creator}")
    embed.set_image(url=thumbnail)
    embed.set_video(url=verification_video)
    embed.add_field(name="__Overview__", value=overview_info, inline=True)
    if len(full_victors) > 1:
        totalLength = len(overview_info) + len(thumbnail) + len(verification_video) + len(embed.title)
        embed.add_field(name="__Challenge victors__", value=full_victors[0])
        totalLength += len(embed.fields[0].value) + len(embed.fields[0].name)
        for i in range(1, len(full_victors)):
            embed.add_field(name="__Challenge victors (cont.)__", value=full_victors[i], inline=True)
            totalLength += len(embed.fields[i].value) + len(embed.fields[i].name)
        print(totalLength)
    else:
        embed.add_field(name="__Challenge victors__", value=full_victors[0], inline=True)
    if len(str(embed._json)) > 5900:
        #for i in range(2):
        embed.remove_field(len(embed.fields) - 1)
        embed.fields[len(embed.fields) - 1].value += f" ... [(10+ more)](https://challengelist.gd/challenges/{g_level['position']})"

    return tuple([embed, f_level['position']]) if lvl_name else embed

@alru_cache()
async def chLeaderboardPageDisable(limit, after, country=None):
    """Checks if next page on player leaderboards should be disabled since player count varies heavily"""
    r = to_json(requests.get(
        f"https://challengelist.gd/api/v1/players/ranking/?limit={limit}{('&nation=' + country) if country else ''}&after={after + limit}",
        headers=headers).text)
    disableNext = True if len(r) == 0 else False
    disableNextAfter = True if len(r) < limit else False
    return (disableNext, disableNextAfter)


async def getLeaderboard(ctx, limit, country, after=None, autocorrect=True):
    title = ""
    cCountry = None if not country else (await correctCountry(ctx, country, limit) if autocorrect else country)
    if type(cCountry) == list:
        await ctx.send(embeds=cCountry[0], components=cCountry[1])
        return None
    print(cCountry, limit, after)
    r = to_json(requests.get(
            f"https://challengelist.gd/api/v1/players/ranking/?limit={limit if limit and limit < 26 else 10}{('&nation=' + cCountry) if cCountry else ('')}&after={after if after else 0}",
            headers=headers).text)

    if not after:
        after = 0
    if not limit:
        limit = 10


    move_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next Page",
        custom_id="nextpage_leaderboard",
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_leaderboard",
        disabled=False if ((after - limit) >= 0) else True
    )
    disableNext, disableNextAft = await chLeaderboardPageDisable(limit, after, cCountry)
    if disableNext or len(r) < limit:
        move_button.disabled = True
    print(after)
    if after == 0 or not after:
        title = f"Challenge List Leaderboard (Top {limit if limit and limit < 26 else 10}{(' in ' + cCountry) if cCountry else ''})"
    else:
        title = f"Challenge List Leaderboard (#{after + 1}-{limit + after}{(' in ' + cCountry) if cCountry else ''})"
    embed = interactions.Embed(color=0xffae00,
                               title=title)
    if len(r) == 0:
        embed.add_field(name="None", value="")
        move_button.disabled, back_button.disabled = True, True
        return (embed, back_button, move_button)
    for player in r:
        country_emoji = f":flag_{player['nationality']['country_code'].lower()}:" if player[
            'nationality'] else ":question:"
        name, rank, points = player['name'], player['rank'], player['score']
        embed.add_field(name=f"__{rank}. {name}__ {country_emoji}", value=f"**{round(points, 3)}** points",
                        inline=False)
    return tuple([embed, back_button, move_button])
