from datetime import datetime
from json import load
from utils import *
import asyncio
import interactions

createdAt = (datetime.now() - datetime(1970, 1, 1)).total_seconds()

token = load(open("token.json"))['token']
agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}

activity = interactions.PresenceActivity(name="VSC", type=interactions.PresenceActivityType.GAME, created_at=createdAt)
presence = interactions.ClientPresence(activities=[activity])
bot = interactions.Client(token=token, presence=presence)

challenge_names_list, challenge_levels_list = (), ()
modals = {}
lvlsLimit = 300

embedCol2 = 0xfafa00

verifySSL = True # turn this off if weird stuff happens

async def updateLevels():
    global lvlsLimit, challenge_names_list, challenge_levels_list
    level_names_list = []
    levels_list = []

    i = 0
    while i <= lvlsLimit:
        r = await requestGET(session, f"https://challengelist.gd/api/v1/demons/?limit=50&after={i}")
        if not r:
            break
        for level in r:
            levels_list.append(level)
            level_names_list.append(level['name'].lower())
        i += 50

    lvlsLimit = len(level_names_list)
    challenge_names_list = tuple(level_names_list)
    challenge_levels_list = tuple(levels_list)
    print("[INFO] Reloaded challenges")

@bot.event
async def on_ready():
    asyncSession = aiohttp.ClientSession(headers=headers)
    await setSession(asyncSession)
    await updateLevels()

    print(f"Bot online and logged in as {bot.me.name} in guilds: {bot.guilds}")
    while True:
        await asyncio.sleep(300)
        await updateLevels()
        await clearCache()

@bot.command(name="leaderboard", description="Shows the top 10 players (currently)",
             options=[interactions.Option(name="page", description="Leaderboard page to show", type=interactions.OptionType.INTEGER, required=False),
                      interactions.Option(name="limit", description="Amount of players to show", type=interactions.OptionType.INTEGER, required=False,
                                          min_value=5, max_value=25, value=10),
                      interactions.Option(name="country", description="Get country leaderboard", type=interactions.OptionType.STRING, required=False)])
async def leaderboard(ctx: interactions.CommandContext, page: int = None, limit: int = None, country: str = None):
    out = await getLeaderboard(ctx, limit, country, after=(page * (limit if limit else 10)) if page else None)
    if type(out) == tuple:
        await ctx.send(embeds=out[0], components=out[1] if not out[2] else [out[1], out[2]])
    else:
        return

@bot.component("backpage_leaderboard")
async def backpage_leaderboard(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    title = ctx.message.embeds[0].title
    country, after, limit = await leaderboardDetails(title)
    after -= limit

    out = await getLeaderboard(ctx, limit, country, after=after, autocorrect=False)
    await ctx.edit(content="", embeds=out[0], components=[out[1], out[2]])

@bot.component("nextpage_leaderboard")
async def nextpage_leaderboard(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    title = ctx.message.embeds[0].title
    country, after, limit = await leaderboardDetails(title)
    after += limit

    out = await getLeaderboard(ctx, limit, country, after=after, autocorrect=False)
    await ctx.edit(content="", embeds=out[0], components=[out[1], out[2]])

@bot.component("leaderboard_playermenu")
async def leaderboard_playersel(ctx: interactions.ComponentContext, val):
    if not await checkInteractionPerms(ctx): return
    out = await getProfile(ctx, val[0].split("_")[2], False, embedCol=embedCol2)
    if out:
        await ctx.edit(content="", embeds=[ctx.message.embeds[0], out], components=ctx.message.components)

@bot.component("countrycorrect")
async def countrycorrect_button(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    if int(ctx.user.id) != int(ctx.message.embeds[0].split("@")[1].split(">")[0]):
        await ctx.send("This is not your command.", ephemeral=True)
        return

    limit = ctx.message.embeds[0].title.split()[3][:-1]
    cCountry = ctx.component.label
    embed = await getLeaderboard(ctx, int(limit), cCountry, 0, autocorrect=False)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next Page",
        custom_id="nextpage_leaderboard",
        disabled=False
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_leaderboard",
        disabled=True
    )
    await ctx.send(embeds=[embed], components=[back_button, move_button])

@bot.command(name="challenges", description="Shows the top challenges",
             options=[interactions.Option(name="limit", description="How many challenges to show (limit is 25)", type=interactions.OptionType.INTEGER, required=False, min_value=5, max_value=25, value=10),
                      interactions.Option(name="page", description="Challenges page (depends on limit parameter if provided)", type=interactions.OptionType.INTEGER, required=False)])
async def challenges(ctx: interactions.CommandContext, limit: int = None, page: int = None):
    if not limit:
        limit = 10

    if page:
        title = f"Challenge List ({limit * page}-{limit * page + limit})"
    else:
        title = f"Challenge List (Top {limit})"

    embed = await getChallenges(ctx, limit, 0 if not page else page * limit, title, challenges_list=challenge_levels_list if challenge_levels_list else None)
    if not embed:
        await ctx.send("**Error:** Page does not exist!")
        return

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled=False
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled=True
    )
    actionRow = interactions.ActionRow(components=[back_button, move_button])
    await ctx.send(embeds=[embed[0]], components=[actionRow, embed[1]])

@bot.component("getchallenges_menu")
async def getchallenges_menusel(ctx: interactions.ComponentContext, option: interactions.SelectOption):
    if not await checkInteractionPerms(ctx): return
    name = option[0].split("_")[1]
    origEmbed = ctx.message.embeds[0]
    origComponents = ctx.message.components

    embed = await showChallenge(ctx, lvl_name=name, challenge_names=challenge_names_list, embedCol=embedCol2)
    embed = embed[0]
    await ctx.edit(content="", embeds=[origEmbed, embed], components=origComponents)

@bot.component("nextpage_challenges")
async def challenges_nextpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return

    embed = ctx.message.embeds[0]
    title = embed.title
    if "-" in title:
        # (#11-20)
        after = int(embed.fields[0].name.split("**")[1].split(".")[0]) - 1
        limit = int(title.split("-")[1].split(")")[0]) - after
        # after = 10
        # limit = 10
        after += limit

    else:
        limit = int(title.split(")")[0].split("Top ")[1])
        after = limit
    title = f"Challenge List (#{after + 1}-{after + limit})"

    embed = await getChallenges(ctx, limit, after, title, challenges_list=challenge_levels_list if challenge_levels_list else None)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled=False if limit*2 + after <= lvlsLimit else True
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled=False if ((after - limit) >= 0) else True
    )
    actionRow = interactions.ActionRow(components=[back_button, move_button])
    await ctx.edit(embeds=[embed[0]], components=[actionRow, embed[1]])

@bot.component("backpage_challenges")
async def challenges_backpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return

    embed = ctx.message.embeds[0]
    title = embed.title
    after = int(embed.fields[0].name.split("**")[1].split(".")[0]) - 1
    limit = int(title.split("-")[1].split(")")[0]) - after
    # after = 10
    # limit = 10
    after -= limit
    title = f"Challenge List (#{after + 1}-{after + limit})" if after > 0 else f"Challenge List (Top {limit})"

    embed = await getChallenges(ctx, limit, after, title, challenges_list=challenge_levels_list if challenge_levels_list else None)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled=False if limit*2 + after <= lvlsLimit else True
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled=False if ((after - limit) >= 0) else True
    )
    actionRow = interactions.ActionRow(components=[back_button, move_button])
    await ctx.edit(embeds=[embed[0]], components=[actionRow, embed[1]])


@bot.command(name="profile", description="Lookup a player's rank/demons beaten/etc.",
             options=[interactions.Option(name="name", description="Player's name", type=interactions.OptionType.STRING, required=True)])
async def profile(ctx: interactions.CommandContext, name: str):
    # SELECT * FROM users
    # WHERE discord_id = {ctx.user.id};
    out = await getProfile(ctx, name, True)
    if not out:
        await ctx.send("**Error:** Player could not be found.")
    else:
        await ctx.send(embeds=out[0], components=list(out[1]))


@bot.command(name="submitrecord", description="Submit a challenge record to the list")
async def submitrecord(ctx: interactions.CommandContext):
    field_challenge = interactions.TextInput(
        style=interactions.TextStyleType.SHORT, label="Challenge (leave blank for \" \")", custom_id="submitrecord_challenge",
        min_length=1, required=False)

    field_player = interactions.TextInput(
        style=interactions.TextStyleType.SHORT, label="Player name", custom_id="submitrecord_player",
        min_length=1, required=True)

    field_video = interactions.TextInput(
        style=interactions.TextStyleType.SHORT, label="Video link (youtube, bilibili, etc.)", custom_id="submitrecord_video",
        min_length=10, required=True)

    field_rawfootage = interactions.TextInput(
        style=interactions.TextStyleType.SHORT, label="Raw footage link", custom_id="submitrecord_rawfootage",
        min_length=10, required=True)

    field_note = interactions.TextInput(
        style=interactions.TextStyleType.SHORT, label="Note (optional)", custom_id="submitrecord_note",
        min_length=1, required=False)

    modal = interactions.Modal(title="Submit List Completion Form", custom_id="modal_submitrecord",
                               components=[field_challenge, field_player, field_video, field_rawfootage, field_note])
    await ctx.popup(modal)

@bot.modal("modal_submitrecord")
async def submitrecord_confirmation(ctx: interactions.ComponentContext, challenge, player, video, raw_footage, note):
    modals.update({int(ctx.user.id): (challenge, player, video, raw_footage, note)})
    cLevel = await correctLevel(ctx, challenge, challenge_names_list, button_id="submitrecord_autocorrect")
    if not cLevel:
        await ctx.send(content=f"<@{ctx.user.id}>, the level you submitted a completion for cannot be found. Please check the name and try again.", ephemeral=True)
        return
    if type(cLevel) == tuple:
        await ctx.send(embed=cLevel[0], components=cLevel[1:])
        return
    if not await requestGET(session, f"https://challengelist.gd/api/v1/players/ranking/?name_contains={player}"):
        await ctx.send(content=f"<@{ctx.user.id}>, the player you submitted a completion for cannot be found. Please check the name and try again.", ephemeral=True)
        return

    embed = interactions.Embed(title="List Completion Confirmation", description=f"<@{ctx.user.id}>, please review the details you submitted for your list completion:")
    for detail in [["Challenge", challenge if challenge else "\" \""], ["Player", player], ["Video link", video], ["Raw footage link", raw_footage], ["Note", note if note else "None"]]:
        embed.add_field(name=detail[0], value=detail[1])

    confirm_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Confirm",
        custom_id="submitrecord_confirm"
    )
    cancel_button = interactions.Button(
        style=interactions.ButtonStyle.DANGER,
        label="Cancel",
        custom_id="submitrecord_cancel"
    )

    await ctx.send(content=f"<@{ctx.user.id}>", embeds=embed, components=[confirm_button, cancel_button], ephemeral=True)

@bot.component("submitrecord_autocorrect")
async def submitrecord_autocorrect(ctx: interactions.ComponentContext):
    modal_data = modals[ctx.user.id]
    challenge, player, video, raw_footage, note = modal_data

    embed = interactions.Embed(title="List Completion Confirmation",
                               description=f"<@{ctx.user.id}>, please review the details you submitted for your list completion:")
    for detail in [["Challenge", challenge if challenge else "\" \""], ["Player", player], ["Video link", video],
                   ["Raw footage link", raw_footage], ["Note", note if note else "None"]]:
        embed.add_field(name=detail[0], value=detail[1])

    confirm_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Confirm",
        custom_id="submitrecord_confirm"
    )
    cancel_button = interactions.Button(
        style=interactions.ButtonStyle.DANGER,
        label="Cancel",
        custom_id="submitrecord_cancel"
    )

    await ctx.send(content=f"<@{ctx.user.id}>", embeds=embed, components=[confirm_button, cancel_button],
                   ephemeral=True)

@bot.component("submitrecord_cancel")
async def submitecord_cancel(ctx: interactions.ComponentContext):
    await ctx.send("**List completion submission cancelled.**")

@bot.component("submitrecord_confirm")
async def submitrecord_confirmed(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx):
        return
    embed = ctx.message.embeds[0]
    challenge = embed.fields[0].value
    player = embed.fields[1].value
    video = embed.fields[2].value
    raw_footage = embed.fields[3].value
    note = embed.fields[4].value if embed.fields[4].value != "None" else None
    try:
        # find ID
        if challenge != "\" \"":
            demon_id = 249 # the exception
        else:
            demon_id = (await requestGET(session, f"https://challengelist.gd/api/v1/records/demons/?name_contains={challenge}"))[0]["id"]

        r = await requestPOST(session, "https://challengelist.gd/api/v1/records/",
                          data={"demon": demon_id, "player": player, "video": video,
                                "raw_footage": raw_footage,
                                "note": (note + f" (Requested with CLBot by {ctx.author.user.username}#{ctx.author.user.discriminator} / {int(ctx.author.user.id)})") if note
                                else f"Requested with CLBot by {ctx.author.user.username}#{ctx.author.user.discriminator} / {int(ctx.author.user.id)}",
                                "progress": 100})
        await ctx.send(f"**<@{ctx.user.id}>**, record sent successfully!**")
    except Exception as e:
        await ctx.send("**Error:** `" + str(e) + "`")

@bot.command(name="getchallenge", description="Lookup completions of a challenge (make sure to use one of the two options)",
             options=[interactions.Option(name="level", description="Level name (not case-sensitive)", type=interactions.OptionType.STRING, required=False),
                      interactions.Option(name="position", description="List position", type=interactions.OptionType.INTEGER, required=False)])
async def getchallenge(ctx: interactions.CommandContext, level: str = None, position: int = None):
    if level or not level and not position:
        if not level:
            out = await showChallenge(ctx, lvl_name=" ", challenge_names=challenge_names_list)
        else:
            out = await showChallenge(ctx, lvl_name=level, challenge_names=challenge_names_list)

        if type(out) == dict:
            out = out['autocorrect_resp']
            await ctx.send(embeds=out[0], components=out[1])
        elif not out:
            return
        else:
            pos = out[1]
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
            await ctx.send(embeds=out[0], components=[lastDemon, nextDemon])
    else:
        out = await showChallenge(ctx, lvl_pos=position)
        lastDemon = interactions.Button(
            style=interactions.ButtonStyle.PRIMARY,
            label="Back",
            custom_id="back_demon",
            disabled=False if (lvlsLimit >= position > 1) else True
        )
        nextDemon = interactions.Button(
            style=interactions.ButtonStyle.PRIMARY,
            label="Next",
            custom_id="next_demon",
            disabled=False if (position <= lvlsLimit) else True
        )
        await ctx.send(embeds=out, components=[lastDemon, nextDemon])

@bot.component("levelcorrect")
async def levelcorrect(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    lvl = ctx.component.label
    embed, position = await showChallenge(ctx, lvl_name=lvl)
    lastDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Back",
        custom_id="back_demon",
        disabled=False if (lvlsLimit >= position > 1) else True
    )
    nextDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next",
        custom_id="next_demon",
        disabled=False if (position <= lvlsLimit) else True
    )

    await ctx.edit(embed=embed, components=[lastDemon, nextDemon])

@bot.component("next_demon")
async def nextchallenge(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    pos = int(await getSubstr(ctx.message.embeds[0].title, "#", ".")) + 1
    embed = await showChallenge(ctx, lvl_pos=pos)

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
    await ctx.edit(content="", embeds=embed, components=[lastDemon, nextDemon])

@bot.component("back_demon")
async def backchallenge(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    pos = int(ctx.message.embeds[0].title.split("#")[1].split(".")[0]) - 1
    embed = await showChallenge(ctx, lvl_pos=pos)

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
    await ctx.edit(content="", embeds=embed, components=[lastDemon, nextDemon])

@bot.component("completions_menu")
async def completions_menusel(ctx: interactions.ComponentContext, val):
    if not await checkInteractionPerms(ctx):
        return

    await ctx.send(embeds=(await showCompletion(val[0])), ephemeral=True)

@bot.component("backpage_completions")
async def completions_backpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx):
        return
    embed = ctx.message.embeds[0]
    player = embed.title.split(" :")[0]
    currPage = int(await getSubstr(ctx.message.components[0].components[0].placeholder, "(", "/"))
    out = await getProfile(ctx, player, completionLinks=True, completionsPage=currPage - 1)
    await ctx.edit(embeds=out[0], components=out[1])

@bot.component("nextpage_completions")
async def completions_nextpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx):
        return
    embed = ctx.message.embeds[0]
    player = embed.title.split(" :")[0]

    currPage = int(await getSubstr(ctx.message.components[0].components[0].placeholder, "(", "/"))
    out = await getProfile(ctx, player, completionLinks=True, completionsPage=currPage + 1)

    await ctx.edit(embeds=out[0], components=out[1])


bot.start()
