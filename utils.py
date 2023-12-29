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

# level IDs and NONGs contributed by h0008 on discord, parsed into json by me
challenge_info = {182: {'levelID': '60805571', 'songPath': 'Downloadable in GD'}, 176: {'levelID': '68963370', 'songPath': 'Downloadable in GD'}, 194: {'levelID': '76767195', 'songPath': '194/818027.mp3'}, 193: {'levelID': '76213334', 'songPath': '193/543943.mp3'}, 293: {'levelID': '8504220', 'songPath': 'Downloadable in GD'}, 217: {'levelID': '69766474', 'songPath': 'Downloadable in GD'}, 10: {'levelID': '61614466', 'songPath': 'Downloadable in GD'}, 229: {'levelID': '50542904', 'songPath': 'Downloadable in GD'}, 249: {'levelID': '67862379', 'songPath': 'Downloadable in GD'}, 305: {'levelID': '94294850', 'songPath': '305/503732.mp3'}, 237: {'levelID': '80993342', 'songPath': '237/412437.mp3'}, 277: {'levelID': '90589855', 'songPath': 'Downloadable in GD'}, 221: {'levelID': '81973761', 'songPath': '221/8800.mp3'}, 267: {'levelID': '86047466', 'songPath': 'Downloadable in GD'}, 278: {'levelID': '90059503', 'songPath': '278/7676.mp3'}, 299: {'levelID': '90432431', 'songPath': '299/70.mp3'}, 259: {'levelID': '73199960', 'songPath': '259/251266.mp3'}, 98: {'levelID': '65348932', 'songPath': 'Downloadable in GD'}, 253: {'levelID': '85701165', 'songPath': 'Downloadable in GD'}, 184: {'levelID': '73859288', 'songPath': 'Downloadable in GD'}, 189: {'levelID': '73227169', 'songPath': 'Downloadable in GD'}, 255: {'levelID': '85856340', 'songPath': 'Downloadable in GD'}, 241: {'levelID': '83951746', 'songPath': 'Downloadable in GD'}, 250: {'levelID': '64919670', 'songPath': 'Downloadable in GD'}, 104: {'levelID': '65496433', 'songPath': '104/447407.mp3'}, 265: {'levelID': '89065307', 'songPath': '265/144.mp3'}, 238: {'levelID': '81932491', 'songPath': 'Downloadable in GD'}, 309: {'levelID': '82292775', 'songPath': 'Downloadable in GD'}, 179: {'levelID': '71530517', 'songPath': 'Downloadable in GD'}, 169: {'levelID': '55392313', 'songPath': 'Downloadable in GD'}, 200: {'levelID': '76663114', 'songPath': 'Downloadable in GD'}, 282: {'levelID': '91790026', 'songPath': '282/1045842.mp3'}, 283: {'levelID': '91995939', 'songPath': '283/500.mp3'}, 260: {'levelID': '87167091', 'songPath': 'Downloadable in GD'}, 270: {'levelID': '64699070', 'songPath': '270/753446.mp3'}, 219: {'levelID': '81023078', 'songPath': '219/481793.mp3'}, 213: {'levelID': '78843980', 'songPath': 'Downloadable in GD'}, 231: {'levelID': '73485796', 'songPath': 'Downloadable in GD'}, 271: {'levelID': '88720184', 'songPath': 'Downloadable in GD'}, 243: {'levelID': '83240981', 'songPath': '243/554.mp3'}, 261: {'levelID': '85492845', 'songPath': 'Downloadable in GD'}, 308: {'levelID': '93060038', 'songPath': 'Downloadable in GD'}, 306: {'levelID': '94141413', 'songPath': 'Downloadable in GD'}, 246: {'levelID': '85287416', 'songPath': 'Downloadable in GD'}, 248: {'levelID': '86301889', 'songPath': 'Downloadable in GD'}, 289: {'levelID': '94008996', 'songPath': '289/9890078.mp3'}, 264: {'levelID': '87199786', 'songPath': 'Downloadable in GD'}, 301: {'levelID': '95575376', 'songPath': 'Downloadable in GD'}, 252: {'levelID': '86892186', 'songPath': '252/555.mp3'}, 2: {'levelID': '57696990', 'songPath': 'Downloadable in GD'}, 303: {'levelID': '95932464', 'songPath': 'Downloadable in GD'}, 216: {'levelID': '75610390', 'songPath': 'Downloadable in GD'}, 304: {'levelID': '90202908', 'songPath': '304/727.mp3'}, 3: {'levelID': '61595973', 'songPath': 'Downloadable in GD'}, 218: {'levelID': '66086403', 'songPath': 'Downloadable in GD'}, 223: {'levelID': '80020830', 'songPath': 'Downloadable in GD'}, 196: {'levelID': '74071137', 'songPath': 'Downloadable in GD'}, 239: {'levelID': '82056731', 'songPath': 'Downloadable in GD'}, 310: {'levelID': '63354658', 'songPath': '310/3996.mp3'}, 290: {'levelID': '89699296', 'songPath': '290/500.mp3'}, 165: {'levelID': '44813027', 'songPath': '165/528176.mp3'}, 258: {'levelID': '68865649', 'songPath': 'Downloadable in GD'}, 138: {'levelID': '67201478', 'songPath': 'Downloadable in GD'}, 168: {'levelID': '68427226', 'songPath': 'Downloadable in GD'}, 4: {'levelID': '62076892', 'songPath': 'Downloadable in GD'}, 268: {'levelID': '86471614', 'songPath': 'Downloadable in GD'}, 269: {'levelID': '87879271', 'songPath': 'Downloadable in GD'}, 296: {'levelID': '91865258', 'songPath': 'Downloadable in GD'}, 275: {'levelID': '88759593', 'songPath': 'Downloadable in GD'}, 307: {'levelID': '78369186', 'songPath': 'Downloadable in GD'}, 191: {'levelID': '73880628', 'songPath': 'Downloadable in GD'}, 256: {'levelID': '87806161', 'songPath': '256/159756.mp3'}, 210: {'levelID': '72619140', 'songPath': 'Downloadable in GD'}, 291: {'levelID': '92636293', 'songPath': '291/983482.mp3'}, 295: {'levelID': '85678458', 'songPath': 'Downloadable in GD'}, 204: {'levelID': '74226067', 'songPath': 'Downloadable in GD'}, 146: {'levelID': '67600557', 'songPath': 'Downloadable in GD'}, 273: {'levelID': '64623383', 'songPath': '273/464352.mp3'}, 236: {'levelID': '83167733', 'songPath': 'Downloadable in GD'}, 233: {'levelID': '83025010', 'songPath': 'Downloadable in GD'}, 9: {'levelID': '59205220', 'songPath': 'Downloadable in GD'}, 287: {'levelID': '94491756', 'songPath': '287/548062.mp3'}, 288: {'levelID': '87635789', 'songPath': '288/137.mp3'}, 300: {'levelID': '95666005', 'songPath': '300/8803.mp3'}, 134: {'levelID': '66663246', 'songPath': 'Downloadable in GD'}, 226: {'levelID': '75236355', 'songPath': 'Downloadable in GD'}, 187: {'levelID': '73235646', 'songPath': 'Downloadable in GD'}, 263: {'levelID': '79014395', 'songPath': '263/40.mp3'}, 292: {'levelID': '90099151', 'songPath': '292/42822.mp3'}, 257: {'levelID': '87558350', 'songPath': '257/14141.mp3'}, 262: {'levelID': '85573922', 'songPath': '262/215.mp3'}, 201: {'levelID': '76750622', 'songPath': '201/56.mp3'}, 284: {'levelID': '94269132', 'songPath': '284/33037.mp3'}, 298: {'levelID': '95143882', 'songPath': '298/34333.mp3'}, 302: {'levelID': '87328218', 'songPath': 'Downloadable in GD'}, 286: {'levelID': '94184192', 'songPath': 'Downloadable in GD'}, 220: {'levelID': '73149969', 'songPath': 'Downloadable in GD'}, 224: {'levelID': '75972097', 'songPath': '224/984786.mp3'}, 242: {'levelID': '80813692', 'songPath': 'Downloadable in GD'}}

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

    challenge_id = f_level['id']
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

    chall_info_dict = challenge_info.get(challenge_id, {'levelID': None, 'songPath': 'N/A'})

    info = [("Creator(s)", creator),
            ("\u200B", "\u200B"),
            ("Verifier", f"[{verifier}]({verification_video})"),
            ("FPS(s)", fps),
            ("Points Awarded", str(points)),
            ("Level ID", chall_info_dict['levelID'] if chall_info_dict['levelID'] else (level_id if level_id else 'N/A'))]
    if chall_info_dict['songPath'] != "N/A":
        info.append(('Song/NONG', ('https://challengelist.rf.gd/nongs/' + chall_info_dict['songPath']) if 'Downloadable' not in chall_info_dict['SongPath'] else 'Downloadable in GD'))

    for field_name, content in info:
        embed.add_field(name=field_name, value=content, inline=True)

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
        embed.set_footer(text=f"Requested by {ctx.user.username} • ID: {str(ctx.user.id)}",
                         icon_url=ctx.user.avatar_url)
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

    for label, completions in zip(["Completed challenges", "Completed challenges (legacy)", "Completed challenges (removed)"], [completed_demons, legacy_demons, removed_demons]):
        embed.add_field(name=label, value=(completions[:charLimit] + "...") if len(completions) > charLimit else completions)
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
async def getChallButtons(lvlsLimit, pos) -> interactions.ActionRow:
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
    actionRow = interactions.ActionRow(components=[lastDemon, nextDemon])
    return actionRow

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
