from autocorrect import *
import aiohttp

verifySSL = True
session = aiohttp.ClientSession()

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}
profiles = {}

async def setSSL(bool_val: bool):
    global verifySSL
    verifySSL = bool_val

async def setSession(newSession: aiohttp.ClientSession):
    global session
    session = newSession

async def clearProfiles():
    global profiles
    profiles = {}

async def requestGET(rSession: aiohttp.ClientSession, url: str) -> dict:
    resp = await rSession.get(url) # asynchronous goodness awaits..
    json = await resp.json()
    return json

async def requestPOST(rSession: aiohttp.ClientSession, url: str, data: dict):
    resp = await rSession.post(url, data=data)
    return resp

@alru_cache(maxsize=1000)
async def getSubstring(s, after, before):
    print(s.index(after) + len(after), s.index(before))
    return s[s.index(after) + len(after): s.index(before)]

@alru_cache(maxsize=400)
async def leaderboardDetails(title):
    """Returns after, limit & country from title."""
    country = None
    after = 0
    if "in" in title:
        country = int(await getSubstring(title, "in ", ")"))
        if "Top" in title:
            # Challenge List Leaderboard (Top 10 in Argentina)
            limit = int(await getSubstring(title, "Top ", " in"))
        else:
            # Challenge List Leaderboard (#11-20 in Argentina)
            after = int(await getSubstring(title, "#", "-")) - 1
            limit = int(await getSubstring(title, "-", " in")) - after
    else:
        if "Top" in title:
            # Challenge List Leaderboard (Top 10)
            limit = int(await getSubstring(title, "op ", ")"))
        else:
            # Challenge List Leaderboard (#11-20)
            after = int(await getSubstring(title, "#", "-")) - 1
            limit = int(await getSubstring(title, "-", ")")) - after

    return country, after, limit

@alru_cache(maxsize=300)
async def calcPoints(n): # calculates list points, n is position
    return round(259.688*(0.962695**n), 2) if n < 101 else 0

# https://www.youtube.com/watch?v=wZxRdKi4uuU
@alru_cache(maxsize=300)
async def getVidThumbnail(url): # video URL to thumbnail
    vCode = url.split("=")[1]
    return "https://i3.ytimg.com/vi/" + vCode + "/maxresdefault.jpg"

@alru_cache(maxsize=300)
async def remLastChar(s: str):
    l = len(s) - 2
    return s[0:l]


async def getChallenges(limit, after, title, challenges_list: list[dict] = None):
    if not challenges_list:
        r = await requestGET(session, f"https://challengelist.gd/api/v1/demons/?limit={limit}&after={after}")
    else:
        r = challenges_list[after: after + limit]
    if not r:
        return None
    embed = interactions.Embed(color=0xffae00, title=title)
    options = []
    for demon in r:
        name, pos, creator, verifier, video = demon['name'], demon['position'], demon['publisher']['name'], \
                                              demon['verifier']['name'], demon['video']
        points = await calcPoints(pos)
        # Add options and embed fields for all levels
        options.append(interactions.SelectOption(
            label=f"{name if name else 'blank'} by {creator}",
            value=f"selectchall_{name if name else 'blank'}",
            description=f"#{pos} - {points} points",
        ))
        embed.add_field(name=f"**{pos}. {name}** by **{creator}**",
                        value=f"Verified by **{verifier}** | [**Video**]({video})\n**{points}** points",
                        inline=True)
    embed.set_thumbnail(await getVidThumbnail(r[0]['video']))
    if not options:
        return
    else:
        selMenu = interactions.SelectMenu(options=options, max_value=1, type=interactions.ComponentType.SELECT, custom_id="getchallenges_menu", placeholder="Select challenge for more info on it..")
        actionRow = interactions.ActionRow(components=[selMenu])
        print(selMenu, actionRow)
        return embed, actionRow

async def showChallenge(context, lvl_name: str = None, lvl_pos: int = None, challenge_names: tuple = None, embedCol: int = 0xffae00):
    g_level = None
    if lvl_name:
        cLevel = await correctLevel(context, lvl_name, challenge_names=challenge_names)
        if type(cLevel) == tuple:
            print(cLevel)
            return tuple(cLevel)
        if not cLevel:
            levels = []
        else:
            levels = await requestGET(session, f"https://challengelist.gd/api/v1/demons/?name_contains={cLevel}")
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

    f_level = (await requestGET(session, f"https://challengelist.gd/api/v1/demons/{g_level['position']}"))['data']

    name, creator, position = f_level['name'], f_level['publisher']['name'], f"#{f_level['position']}"
    verifier, verification_video, level_id = f_level['verifier']['name'], f_level['video'], f_level['level_id']
    fps = f_level['fps'] if f_level['fps'] else "Any"

    points = await calcPoints(f_level['position']) if f_level['position'] < 101 else "None"
    thumbnail = await getVidThumbnail(verification_video)

    full_victors = []
    curr_victors_msg = ""

    vLen = 0
    for completion in f_level['records']:
        if completion['status'] != "approved" or completion['player']['banned']:  # skip the record if this happens
            continue

        p_flag = f" :flag_{completion['nationality']['country_code'].lower()}:" if completion['nationality'] else ":united_nations:"
        p_name = completion['player']['name']
        c_progress = completion['progress']

        proof = completion['video']

        if c_progress == 100:
            v_data = f"**[{p_name}]({proof})**{p_flag}"
            if len(v_data) + vLen > 900:
                curr_victors_msg = await remLastChar(curr_victors_msg)
                full_victors.append(curr_victors_msg)
                curr_victors_msg = v_data + ", "
                vLen = len(v_data)
                continue
            vLen += len(v_data)
            curr_victors_msg += v_data + ", "
    full_victors.append(await remLastChar(curr_victors_msg))

    embed = interactions.Embed(color=embedCol, title=f"{position}. {name}")
    embed.set_thumbnail(url=thumbnail)

    info = (("Creator(s)", creator),
            ("Verifier", f"[{verifier}]({verification_video})"),
            ("Level ID", level_id if level_id else "N/A"),
            ("FPS(s)", fps),
            ("Points Awarded", str(points)))

    for i in info:
        embed.add_field(name=i[0], value=i[1], inline=True)

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
    while len(str(embed._json)) > 5900: # shorten amount of victors if too large
        embed.remove_field(len(embed.fields) - 1)
        l = len(embed.fields) - 1 # how many embed fields there are
        embed.fields[l].value += f" ... [(10+ more)](https://challengelist.gd/challenges/{g_level['position']})"
        embed.fields[l].name = embed.fields[l].name.split('-')[0] + '...)'
    print(embed)
    return embed if not lvl_name else embed, f_level['position']

@alru_cache(maxsize=300)
async def chLeaderboardPageDisable(limit, after, country=None):
    """Checks if next page on player leaderboards should be disabled since player count varies heavily"""
    r = await requestGET(session, f"https://challengelist.gd/api/v1/players/ranking/?limit={limit}{('&nation=' + country) if country else ''}&after={after + limit}")
    disableNext = True if len(r) == 0 else False
    disableNextAfter = True if len(r) < limit else False
    return disableNext, disableNextAfter


async def getLeaderboard(ctx, limit, country, after=None, autocorrect=True):
    """"""
    cCountry = None if not country else (await correctCountry(ctx, country, limit) if autocorrect else country)
    if type(cCountry) == list:
        await ctx.send(embeds=cCountry[0], components=cCountry[1]) # send autocorrect embed form
        return None

    r = await requestGET(session, f"https://challengelist.gd/api/v1/players/ranking/?limit={limit if limit and limit < 26 else 10}{('&nation=' + cCountry) if cCountry else ''}&after={after if after else 0}")
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
        return embed, back_button, move_button
    for player in r:
        country_emoji = f":flag_{player['nationality']['country_code'].lower()}:" if player['nationality'] else ":united_nations:"
        name, rank, points = player['name'], player['rank'], round(player['score'], 2)
        # Leaderboard options & fields
        options.append(interactions.SelectOption(
            label=f"{name}",
            value=f"leaderboard_selectplayer_{name}",
            description=f"#{rank} - {points} points",
        ))
        embed.add_field(name=f"{rank}. {name} {country_emoji}", value=f"**{points}** points",
                        inline=True)

    if not options:
        return tuple([embed, back_button, move_button])
    else:
        actionRow = interactions.ActionRow(components=[back_button, move_button])
        selMenu = interactions.SelectMenu(options=options, max_value=1, type=interactions.ComponentType.SELECT, custom_id="leaderboard_playermenu", placeholder="Select player for more info on them..")
        actionRow2 = interactions.ActionRow(components=[selMenu])
        return tuple([embed, actionRow, actionRow2])

async def getProfile(name, completionLinks: bool = False, embedCol: int = 0xffae00):
    """Returns a profile embed or returns ``None`` if player can't be found."""
    p = await requestGET(session, f"https://challengelist.gd/api/v1/players/ranking/?name_contains={name}")
    if not p:
        # adding an autocorrect to profiles would probably require indexing every player (over 300 and counting).
        # that might not be ideal
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

        p_id = p['id']

        cachedEmbed = profiles.get(p_id)
        if cachedEmbed:
            return cachedEmbed

        rank = p['rank']
        badge = "" if rank > 3 else {1: ':first_place:', 2: ':second_place:', 3: ':third_place:'}[rank]
        more_details = (await requestGET(session, f"https://challengelist.gd/api/v1/players/{p_id}"))[
            'data']

        for sLevels in ['created', 'published', 'verified', 'records']: # very swag python code
            more_details.update({sLevels: sorted(more_details[sLevels], key=lambda pos: pos['position'] if sLevels != 'records' else pos['demon']['position'])})

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
        options = []
        for record in more_details['records']:
            if record['demon']['position'] > 100:
                if "❌" in record['demon']['name']:
                    removed_demons.append(f"*{record['demon']['name']}*")
                else:
                    legacy_demons.append(f"{record['demon']['name']}")
            else:
                completed_demons.append(f"{record['demon']['name']}")
            if completionLinks:
                options.append(interactions.SelectOption(label=f"#{record['demon']['position']}. {record['demon']} ", value=f'completion_{record["demon"]["name"]}_{name}'))

        # i wish there was a better way to do this......
        completed_demons = ', '.join(completed_demons) if completed_demons else "None"
        legacy_demons = ', '.join(legacy_demons) if legacy_demons else "None"
        removed_demons = ', '.join(removed_demons) if removed_demons else "None"

        cCountry = f":flag_{p['nationality']['country_code'].lower()}:" if p['nationality'] else ":united_nations:"

        embed = interactions.Embed(color=embedCol, title=f"{p['name']} {cCountry}")
        thumb = None
        if more_details['records'] and more_details['records'][0]['status'] == 'approved':
            thumb = await getVidThumbnail(more_details['records'][0]['video'])

        embed.add_field(name="Nationality", value=f"{p['nationality']['nation'] if p['nationality'] else 'N/A'}", inline=True)
        embed.add_field(name="Rank", value=f"#{rank} {badge}", inline=True)
        embed.add_field(name="List Points", value=f"{round(p['score'], 2)}", inline=True)
        embed.add_field(name="Challenges created", value=created_demons, inline=True)
        # embed.add_field(name="Published challenges", value=published_demons, inline=True)
        embed.add_field(name="Verified challenges", value=verified_demons, inline=True)

        embed.add_field(name="Completed challenges",
                        value=(completed_demons[:700] + "...") if len(completed_demons) > 700 else completed_demons)
        embed.add_field(name="Completed challenges (legacy)",
                        value=(legacy_demons[:500] + "...") if len(legacy_demons) > 500 else legacy_demons)
        embed.add_field(name="Completed challenges (removed)",
                        value=(removed_demons[:700] + "...") if len(removed_demons) > 700 else removed_demons)
        embed.set_thumbnail(url=thumb)
        profiles.update({p_id: embed})
        return embed


async def checkInteractionPerms(ctx: interactions.ComponentContext):
    pass
