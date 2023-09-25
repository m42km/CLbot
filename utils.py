from async_lru import alru_cache
from autocorrect import *
from req import *
from misc import discToListUser, listToDisc, getPointsInt
from math import exp, log
verifySSL = True

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}
profileCache = {} # profile embed cache
profileCompsCache = {} # profile completion cache
# sample: {384: {'completions': completionsJson, 'baseEmbed': embed, 'detailComps': components}}
embedCol2 = 0xfafa00

async def clearCache():
    global profileCache
    profileCache = {}

@alru_cache(maxsize=2000)
async def getLinkInfo(link: str) -> tuple:
    new = link.replace("-", " ").replace(":", "(").replace(";", ")")
    args = new.split("=")[1].split("|")
    # limit|after|title
    limit, after, title = int(args[0]), int(args[1]), args[2]
    return limit, after, title

@alru_cache(maxsize=2000)
async def getChallsTitle(limit: int, page: int = None, after: int = None) -> str:
    if not page and not after:
        return f"Challenge List (Top {limit})"
    levelStart = ((limit * page) if page else after) + 1
    levelEnd = levelStart + limit - 1
    if levelEnd > 100 and levelStart < 100:
        return f"Challenge List (#{levelStart}-100 and #101-{levelEnd} Legacy List)"
    if levelStart >= 100:
        return f"Challenge Legacy List (#{levelStart}-{levelEnd})"

    return f"Challenge List (#{levelStart}-{levelEnd})"

@alru_cache(maxsize=2000)
async def buildChallsLinkStr(limit, page, title: str) -> str:
    newTitle = title.replace(" ", "-")
    currLink = f"https://challengelist.gd/challenges?inf={limit}|{page*limit}|{newTitle}"
    fixedLink = currLink.replace("(", ":").replace(")", ";")
    return fixedLink

async def packActionRows(options) -> list:
    """Packs large amounts of completion options in multiple action rows."""
    optionsAmt = 20
    fOptions = [options[x:x+optionsAmt] for x in range(0, len(options), optionsAmt)]
    menus = []
    optionsLength = len(fOptions)
    for opts in enumerate(fOptions):
        selMenu = interactions.SelectMenu(options=opts[1], placeholder=f"({opts[0] + 1}/{optionsLength}) Select completion for more info...", custom_id="completions_menu")
        actionRow = interactions.ActionRow(components=[selMenu])
        menus.append(actionRow)
    return menus

@alru_cache(maxsize=500)
async def getChallButtons(lvlsLimit, pos):
    lastDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Back",
        custom_id="back_demon",
        disabled=False if (lvlsLimit >= pos > 1) else True
    )
    nextDemon = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next",
        custom_id="next_demon",
        disabled=False if (pos <= lvlsLimit) else True
    )
    return lastDemon, nextDemon

@alru_cache(maxsize=1000)
async def getSubstr(s: str, after: str, before: str) -> str:
    return s[s.index(after) + len(after): s.index(before)]

@alru_cache(maxsize=500)
async def leaderboardDetails(title) -> tuple:
    """Returns after, limit & country from title."""
    country = None
    after = 0
    if "in" in title:
        country = int(await getSubstr(title, "in ", ")"))
        if "Top" in title:
            # Challenge List Leaderboard (Top 10 in Argentina)
            limit = int(await getSubstr(title, "Top ", " in"))
        else:
            # Challenge List Leaderboard (#11-20 in Argentina)
            after = int(await getSubstr(title, "#", "-")) - 1
            limit = int(await getSubstr(title, "-", " in")) - after
    else:
        if "Top" in title:
            # Challenge List Leaderboard (Top 10)
            limit = int(await getSubstr(title, "op ", ")"))
        else:
            # Challenge List Leaderboard (#11-20)
            after = int(await getSubstr(title, "#", "-")) - 1
            limit = int(await getSubstr(title, "-", ")")) - after

    return country, after, limit

@alru_cache(maxsize=500)
async def calcPoints(n) -> float: # calculates list points, n is position
    return round(250 * exp(log(250 / 15) / (-99) * (n - 1)), 2) if n < 101 else 0

# https://www.youtube.com/watch?v=wZxRdKi4uuU
@alru_cache(maxsize=300)
async def getVidThumbnail(url, main=True) -> str: # video URL to thumbnail
    vCode = url.split("=")[1]
    return "https://i3.ytimg.com/vi/" + vCode + ("/maxresdefault.jpg" if main else "/1.jpg")

@alru_cache(maxsize=300)
async def remLastChar(s: str) -> str:
    length = len(s) - 2
    return s[0:length]

async def checkInteractionPerms(ctx: interactions.ComponentContext) -> bool:
    if not str(ctx.user.id) in ctx.message.embeds[0].footer.text:
        await ctx.send(f"<@{int(ctx.user.id)}>, you cannot interact with this bot message. Please run your own command.", ephemeral=True)
        return False
    else:
        return True

async def getChallenges(ctx, limit, after, title, challenges_list: tuple = None):
    if not challenges_list:
        r = await requestGET(f"https://challengelist.gd/api/v1/demons/?limit={limit}&after={after}")
    else:
        r = challenges_list[after: after + limit]
    if not r:
        return None
    embed = interactions.Embed(color=0xffae00, title=title)
    options = []
    mod = 2
    for i, demon in enumerate(r):
        name, pos, creator, verifier, video = demon['name'], demon['position'], demon['publisher']['name'], \
                                              demon['verifier']['name'], demon['video']
        points = await calcPoints(pos)
        # Add options and embed fields for all levels
        options.append(interactions.SelectOption(
            label=f"{name if name else 'blank'} by {creator}",
            value=f"selectchall_{pos}",
            description=f"#{pos} - {points} points",
        ))
        embed.add_field(name=f"**{pos}. {name}** by **{creator}**",
                        value=f"Verified by [**{verifier}**]({video}) - **{points}** points",
                        inline=True)
        if i % mod == 0:
            embed.add_field(name="\u200B", value="\n", inline=True)
    embed.add_field(name="\u200B", value="\n", inline=True)
    wLink = await buildChallsLinkStr(limit, round(after / limit), title)
    embed.set_video(url=wLink)
    embed.set_thumbnail(url=(await getVidThumbnail(r[0]['video'])))
    embed.set_footer(text=f"Requested by {ctx.user.username} • ID: {str(ctx.user.id)}", icon_url=ctx.user.avatar_url)
    embed.description = f"Challenge List Website: [Link]({wLink})"

    if not options:
        return
    else:
        selMenu = interactions.SelectMenu(options=options, max_value=1, type=interactions.ComponentType.SELECT, custom_id="getchallenges_menu", placeholder="Select challenge for more info on it..")
        actionRow = interactions.ActionRow(components=[selMenu])
        return embed, actionRow

async def showChallenge(ctx, lvl_name: str = None, lvl_pos: int = None, challenge_names: tuple = None, embedCol: int = 0xffae00):
    g_level = None
    if lvl_name:
        cLevel = await correctLevel(ctx, lvl_name, challenge_names=challenge_names)
        if type(cLevel) == tuple:
            return {'autocorrect_resp': tuple(cLevel)}
        if not cLevel:
            levels = []
        else:
            levels = await requestGET(f"https://challengelist.gd/api/v1/demons/?name_contains={cLevel}")
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
            await ctx.send("**Error:** Couldn't find any levels with that name. Did you misspell it or something?")
            return None
        else:
            g_level = levels[0]
    elif lvl_pos:
        g_level = {"position": lvl_pos}

    f_level = (await requestGET(f"https://challengelist.gd/api/v1/demons/{g_level['position']}"))['data']

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

        p_flag = f" :flag_{completion['nationality']['country_code'].lower()}:" if completion['nationality'] else " :united_nations:"
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
    embed.set_footer(text=f"Requested by {ctx.user.username} • ID: {str(ctx.user.id)}", icon_url=ctx.user.avatar_url)
    info = (("Creator(s)", creator),
            ("\u200B", "\u200B"),
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
    while len(str(embed._json)) > 5500: # shorten amount of victors if too large
        embed.remove_field(len(embed.fields) - 1)
        lenFields = len(embed.fields) - 1 # how many embed fields there are
        embed.fields[lenFields].value += f" ... [(10+ more)](https://challengelist.gd/challenges/{g_level['position']})"
        embed.fields[lenFields].name = embed.fields[lenFields].name.split('-')[0] + '...)'
    return embed if lvl_pos else (embed, f_level['position'])

@alru_cache(maxsize=300)
async def chLeaderboardPageDisable(limit, after, country=None):
    """Checks if next page on player leaderboards should be disabled since player count varies heavily"""
    r = await requestGET(
        f"https://challengelist.gd/api/v1/players/ranking/?limit={limit}{('&nation=' + country) if country else ''}&after={after + limit}")
    disableNext = True if len(r) == 0 else False
    disableNextAfter = True if len(r) < limit else False
    return disableNext, disableNextAfter


async def getLeaderboard(ctx, limit, country, after=None, autocorrect=True):
    """"""
    cCountry = None if not country else (await correctCountry(ctx, country, limit) if autocorrect else country)
    if type(cCountry) == list:
        await ctx.send(embeds=cCountry[0], components=cCountry[1]) # send autocorrect embed form
        return None

    r = await requestGET(
        f"https://challengelist.gd/api/v1/players/ranking/?limit={limit if limit and limit < 26 else 10}{('&nation=' + cCountry) if cCountry else ''}&after={after if after else 0}")
    if not after:
        after = 0
    if not limit:
        limit = 10

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
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

    if after == 0 or not after:
        title = f"Challenge List Leaderboard (Top {limit}{(' in ' + cCountry) if cCountry else ''})"
    else:
        title = f"Challenge List Leaderboard (#{after + 1}-{limit + after}{(' in ' + cCountry) if cCountry else ''})"

    embed = interactions.Embed(color=0xffae00, title=title)
    embed.set_footer(text=f"Requested by {ctx.user.username} • ID: {str(ctx.user.id)}", icon_url=ctx.user.avatar_url)
    if len(r) == 0:
        embed.add_field(name="None", value="")
        move_button.disabled, back_button.disabled = True, True
        return embed, back_button, move_button
    for i, player in enumerate(r):
        country_emoji = f":flag_{player['nationality']['country_code'].lower()}:" if player['nationality'] else " :united_nations:"
        name, rank, points = player['name'], player['rank'], round(player['score'], 2)
        # Leaderboard options & fields
        options.append(interactions.SelectOption(
            label=f"{name}",
            value=f"leaderboard_selectplayer_{name}",
            description=f"#{rank} - {points} points",
        ))
        embed.add_field(name=f"{rank}. {name} {country_emoji}", value=f"**{points}** points",
                        inline=True)
        if i % 2 == 0:
            embed.add_field(name="\u200B", value="\u200B", inline=True)
    if not options:
        return tuple([embed, back_button, move_button])
    else:
        actionRow = interactions.ActionRow(components=[back_button, move_button])
        selMenu = interactions.SelectMenu(options=options, max_value=1, type=interactions.ComponentType.SELECT, custom_id="leaderboard_playermenu", placeholder="Select player for more info on them..")
        actionRow2 = interactions.ActionRow(components=[selMenu])
        return tuple([embed, actionRow, actionRow2])

async def getProfileCompletions(name: str, p_id: int, completions: list, page: int = 1):
    if not completions:
        return None
    cachedData = profileCompsCache.get(p_id)
    if cachedData:
        return cachedData[0][page - 1], cachedData[1][page - 1]
    opts = []
    buttonSets = []
    for record in completions:
        opts.append(interactions.SelectOption(label=f"#{record['demon']['position']}. {record['demon']['name']}",
                                              value=f'comp,{record["demon"]["name"]},{name},{record["video"][32:]},{record["demon"]["position"]}',
                                              description=f"{await calcPoints(record['demon']['position'])} points"))
    fOpts = await packActionRows(opts)
    optionsLength = len(fOpts)
    for menu in enumerate(fOpts):
        backButton = interactions.Button(label="Last Page (Completions)",
                                         custom_id="backpage_completions",
                                         style=interactions.ButtonStyle.PRIMARY,
                                         disabled=True if menu[0] == 0 else False)

        nextButton = interactions.Button(label="Next Page (Completions)",
                                         custom_id="nextpage_completions",
                                         style=interactions.ButtonStyle.SUCCESS,
                                         disabled=True if menu[0] >= optionsLength - 1 else False)

        buttonActionRow = interactions.ActionRow(components=[backButton, nextButton])
        buttonSets.append(buttonActionRow)

    comps = (fOpts, buttonSets)

    profileCompsCache.update({p_id: comps})
    # comps = tuple[ActionRow], tuple[tuple[Button]]
    return fOpts[0], buttonSets[0]
    # returns one actionrow and a tuple of two buttons

async def getProfile(ctx, name: str = None, discUser: interactions.User = None, completionLinks: bool = False, embedCol: int = 0xffae00, completionsPage: int = 1):
    """Returns a profile embed, a profile embed and components or returns ``None`` if player can't be found."""

    playerDiscordID = None
    coolStars = None
    if name:
        p = await requestGET(f"https://challengelist.gd/api/v1/players/ranking/?name_contains={name}")
        if not p:
            # adding an autocorrect to profiles would probably require indexing every player (over 300 and counting).
            # that might not be ideal
            await ctx.send("**Error**: Could not find a account on the Challenge List with that name.")
            return None
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
        name = p['name']
        playerDiscordID = await listToDisc(name)
        if playerDiscordID == 0:
            playerDiscordID = None
    elif not discUser:
        res = await discToListUser(str(ctx.user.id))
        playerDiscordID = str(ctx.user.id)
        if res != 0:
            p = await requestGET(f"https://challengelist.gd/api/v1/players/ranking/?name_contains={res}")
            p = p[0]
            p_id, name = p['id'], p['name']
        else:
            await ctx.send("Your Challenge List account is not linked to your Discord account or an error has occurred. Try again later or ask a staff member to resolve it for you.")
            return
    else:
        res = await discToListUser(str(discUser.id))
        playerDiscordID = str(discUser.id)
        if res != 0:
            p = await requestGET(f"https://challengelist.gd/api/v1/players/ranking/?name_contains={res}")
            p = p[0]
            p_id, name = p['id'], p['name']
        else:
            await ctx.send("Error: That Discord user does not have a Challenge List account linked to them. Please try again later.")
            return

    # cached embeds & completions
    cachedData = profileCache.get(p_id)
    if cachedData:
        embed = cachedData['baseEmbed']
        if completionLinks:
            components = await getProfileCompletions(name, p_id, cachedData['completions'], completionsPage)
            return embed, list(components)
        else:
            return embed

    rank = p['rank']
    badge = "" if rank > 3 else {1: ':first_place:', 2: ':second_place:', 3: ':third_place:'}[rank]
    more_details = (await requestGET(f"https://challengelist.gd/api/v1/players/{p_id}"))['data']

    for sLevels in ['created', 'published', 'verified', 'records']: # very swag python code
        more_details.update({sLevels: sorted(more_details[sLevels], key=lambda pos: pos['position'] if sLevels != 'records' else pos['demon']['position'])})

    created_demons = []
    for demon in more_details['created']:
        created_demons.append(f"**{demon['name']}** (#{demon['position']})")
    created_demons = ', '.join(created_demons) if created_demons else "None"

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
        options.append(interactions.SelectOption(label=f"#{record['demon']['position']}. {record['demon']['name']} ",
                                                 value=f'comp|{record["demon"]["name"]}|{p["name"]}|{record["video"][32:]}|{record["demon"]["position"]}',
                                                 description=f"{await calcPoints(record['demon']['position'])} points"))

    # i wish there was a better way to do this......
    completed_demons = ', '.join(completed_demons) if completed_demons else "None"
    legacy_demons = ', '.join(legacy_demons) if legacy_demons else "None"
    removed_demons = ', '.join(removed_demons) if removed_demons else "None"

    cCountry = f":flag_{p['nationality']['country_code'].lower()}:" if p['nationality'] else ":united_nations:"

    embed = interactions.Embed(color=embedCol, title=f"{p['name']} {cCountry}")

    thumb = None
    if more_details['records'] and more_details['records'][0]['status'] == 'approved':
        thumb = await getVidThumbnail(more_details['records'][0]['video'])

    charLimit = 125

    embed.add_field(name="Nationality", value=f"{p['nationality']['nation'] if p['nationality'] else 'N/A'}", inline=True)
    embed.add_field(name="Rank", value=f"#{rank} {badge}", inline=True)
    embed.add_field(name="List Points", value=f"{round(p['score'], 2)}", inline=True)
    if playerDiscordID:
        embed.add_field(name="Discord", value=f"<@{playerDiscordID}>", inline=True)
        embed.add_field(name="Cool-Stars", value=str(await getPointsInt(int(playerDiscordID))), inline=True)
    embed.add_field(name="Challenges created", value=created_demons, inline=True)
    embed.add_field(name="Verified challenges", value=verified_demons, inline=True if len(verified_demons) < 200 else False)

    embed.add_field(name="Completed challenges",
                    value=(completed_demons[:charLimit] + "...") if len(completed_demons) > charLimit else completed_demons)
    embed.add_field(name="Completed challenges (legacy)",
                    value=(legacy_demons[:charLimit] + "...") if len(legacy_demons) > charLimit else legacy_demons)
    embed.add_field(name="Completed challenges (removed)",
                    value=(removed_demons[:charLimit] + "...") if len(removed_demons) > charLimit else removed_demons)
    embed.set_thumbnail(url=thumb)
    # sample: {384: {'completions': completionsJson, 'baseEmbed': embed, 'detailComps': components}}
    components = None
    if completionLinks:
        components = await getProfileCompletions(name, p_id, more_details['records'], page=completionsPage)

    profileCache.update({p_id: {"baseEmbed": embed, "completions": more_details['records']}})
    if completionLinks:
        embed.set_footer(text=f"Requested by {ctx.user.username} • ID: {str(ctx.user.id)}",
                         icon_url=ctx.user.avatar_url)
    return embed if not completionLinks else [embed, components]

@alru_cache(maxsize=512)
async def getChallButtons(lvlsLimit, pos) -> tuple:
    lastDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Back",
        custom_id="back_demon",
        disabled=False if (lvlsLimit >= pos > 1) else True
    )
    nextDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next",
        custom_id="next_demon",
        disabled=False if (pos <= lvlsLimit) else True
    )
    return lastDemon, nextDemon

async def showCompletion(valsString: str):
    vals = valsString.split(",")
    name, player, link, pos = vals[1], vals[2], "https://youtube.com/watch?v=" + vals[3], vals[4]
    suffix = "'s" if not name.lower().endswith('s') and not name.lower().endswith('z') else "'"

    embed = interactions.Embed(title=f"{player}{suffix} {name} Completion", color=embedCol2)
    embed.add_field(name="Completion Link", value=link)
    embed.add_field(name="Position", value="#" + pos, inline=True)
    embed.add_field(name="List Points", value=str(await calcPoints(int(pos))), inline=True)

    img = await getVidThumbnail(link)
    thumb = await getVidThumbnail(link, main=False)
    embed.set_image(url=img)
    embed.set_thumbnail(url=thumb)
    return embed
