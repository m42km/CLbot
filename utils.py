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
@alru_cache(maxsize=250)
async def getVidThumbnail(url): # video URL to thumbnail
    vCode = url.split("=")[1]
    #print("https://img.youtube.com/vi/" + vCode + "0.jpg")
    return "https://img.youtube.com/vi/" + vCode + "/maxresdefault.jpg"

@alru_cache(maxsize=200)
async def remLastChar(s: str):
    l = len(s) - 2
    return s[0:l]

@alru_cache()
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

@alru_cache()
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

    # l_overview_info = [f"Verified by **{verifier}**",
    #                    f"**FPS:** {fps}",
    #                    f"**Verification: [Link]({verification_video})**",
    #                    f"**ID:** {level_id}",
    #                    f"**Points Awarded:** {points}"]
    # overview_info = "\n".join(l_overview_info)

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
    embed = interactions.Embed(color=0xffae00, title=f"{position}. {name}")
    embed.set_thumbnail(url=thumbnail)
    embed.add_field(name="Creator(s)", value=creator, inline=True)
    embed.add_field(name="Verifier", value=f"[{verifier}]({verification_video})", inline=True)
    embed.add_field(name="Level ID", value=level_id if level_id else "N/A", inline=True)
    embed.add_field(name="FPS(s)", value=fps, inline=True)
    embed.add_field(name="Points Awarded", value=str(points), inline=True)
    if len(full_victors) > 1:
        victorCount = round(full_victors[0].count(' ') / 2)
        embed.add_field(name=f"Challenge victors (1-{victorCount})", value=full_victors[0])
        for i in range(1, len(full_victors)):
            if full_victors[i].count(",") > 0:
                embed.add_field(name=f"Challenge victors ({victorCount + 1}-{victorCount + full_victors[i].count(',') + 3})", value=full_victors[i], inline=True if victorCount > 0 else False)
            else:
                embed.add_field(name=f"Challenge victor ({victorCount + 2})", value=full_victors[i], inline=True)
            victorCount += full_victors[i].count(',') + 1
    else:
        embed.add_field(name="Challenge victors", value=full_victors[0] if full_victors[0] else "None!", inline=False)
    while len(str(embed._json)) > 5900:
        #for i in range(2):
        embed.remove_field(len(embed.fields) - 1)
        l = len(embed.fields) - 1
        embed.fields[l].value += f" ... [(10+ more)](https://challengelist.gd/challenges/{g_level['position']})"
        embed.fields[l].name = embed.fields[l].name.split('-')[0] + '...)'
    print(embed)
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
        custom_id="nextpage_leaderboard"
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_leaderboard",
        disabled=False if ((after - limit) >= 0) else True
    )

    options = []

    disableNext, disableNextAft = await chLeaderboardPageDisable(limit, after, cCountry)
    if disableNext or len(r) < limit:
        move_button.disabled = True
    print(after)
    if after == 0 or not after:
        title = f"Challenge List Leaderboard (Top {limit}{(' in ' + cCountry) if cCountry else ''})"
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
        name, rank, points = player['name'], player['rank'], round(player['score'], 2)
        options.append(interactions.SelectOption(
            label=f"{name}",
            value=f"leaderboard_selectplayer_{name}",
            description=f"#{rank} - {points} points",
        ))
        embed.add_field(name=f"{rank}. {name} {country_emoji}", value=f"**{points}** points",
                        inline=False)

    if options == []:
        return tuple([embed, back_button, move_button])
    else:
        actionRow = interactions.ActionRow(components=[back_button, move_button])
        selMenu = interactions.SelectMenu(options=options, max_value=1, type=interactions.ComponentType.SELECT, custom_id="leaderboard_playermenu")
        actionRow2 = interactions.ActionRow(components=[selMenu])
        return tuple([embed, actionRow, actionRow2])

async def getProfile(ctx, name):
    p = to_json(
        requests.get(f"https://challengelist.gd/api/v1/players/ranking/?name_contains={name}", headers=headers).text)
    if not p:
        await ctx.send("Couldn't find any player with that name, try again (a typo maybe?)")
        return None
    else:
        # get the correct user
        if len(p) > 1:
            i = 0
            for player in p:
                if len(player['name']) == name:
                    p = p[i]
                    break
                else:
                    i += 1
            if len(p) > 1:
                p = p[0]
        else:
            p = p[0]

        id = p['id']
        rank = p['rank']
        badge = "" if rank > 3 else {1: ':first_place:', 2: ':second_place:', 3: ':third_place:'}[rank]
        more_details = to_json(requests.get(f"https://challengelist.gd/api/v1/players/{id}", headers=headers).text)[
            'data']
        created_demons = []
        for demon in more_details['created']:
            created_demons.append(f"**{demon['name']}** (#{demon['position']})")
        created_demons = ', '.join(created_demons) if created_demons else "None"

        published_demons = []
        for demon in more_details['published']:
            published_demons.append(f"**{demon['name']}** (#{demon['position']})")
        published_demons = ', '.join(published_demons) if published_demons else "None"

        verified_demons = []
        for demon in more_details['verified']:
            verified_demons.append(f"**{demon['name']}** (#{demon['position']})")
        verified_demons = ', '.join(verified_demons) if verified_demons else "None"

        completed_demons, legacy_demons, removed_demons = [], [], []
        for record in more_details['records']:
            if record['demon']['position'] > 100:
                if "❌" in record['demon']['name']:
                    removed_demons.append(f"*{record['demon']['name']}*")
                else:
                    legacy_demons.append(f"{record['demon']['name']}")
            else:
                completed_demons.append(f"{record['demon']['name']}")

        # i wish there was a better way to do this......
        completed_demons = ', '.join(completed_demons) if completed_demons else "None"
        legacy_demons = ', '.join(legacy_demons) if legacy_demons else "None"
        removed_demons = ', '.join(removed_demons) if removed_demons else "None"

        cCountry = f":flag_{p['nationality']['country_code'].lower()}:" if p['nationality'] else ":question:"

        embed = interactions.Embed(color=0xffae00, title=f"{p['name']} {cCountry}")

        embed.add_field(name="Nationality", value=f"{p['nationality']['nation'] if p['nationality'] else 'N/A'}", inline=True)
        embed.add_field(name="Rank", value=f"#{rank} {badge}", inline=True)
        embed.add_field(name="List Points", value=f"{round(p['score'], 2)}", inline=True)
        embed.add_field(name="Challenges created", value=created_demons, inline=True)
        embed.add_field(name="Published challenges", value=published_demons, inline=True)
        embed.add_field(name="Verified challenges", value=verified_demons, inline=True)

        embed.add_field(name="Completed challenges",
                        value=(completed_demons[:1021] + "...") if len(completed_demons) > 1020 else completed_demons, inline=True)
        embed.add_field(name="Completed challenges (legacy)",
                        value=(legacy_demons[:1021] + "...") if len(legacy_demons) > 1020 else legacy_demons)
        embed.add_field(name="Completed challenges (removed)",
                        value=(removed_demons[:1021] + "...") if len(removed_demons) > 1020 else removed_demons)
        return embed

