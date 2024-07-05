from dotenv import load_dotenv
from json import load

load_dotenv()

f = open("configdiscord.json", "r")
config = load(f)
f.close()

from utils import *
from misc import *
import asyncio
import interactions
import interactions.models.discord.components

createdAt = (datetime.now() - datetime(1970, 1, 1)).total_seconds()
currDaily = 0
currDailies = {}
dailyCol = 0xfafa45

token = os.getenv("TOKEN")

dailySubsChannelID = config['channels']['dailyCompletions']
dailyQueueChannelID = config['channels']['dailyModsQueue']
dailyAnnounceChannelID = config['channels']['dailyAnnouncements']

dailySubsChannel = None
dailyQueueChannel = None
dailyAnnounceChannel = None
doubleFriday = None

dailyCurrSubs = {"daily": {}, "daily1": {}, "daily2": {}, "weekly": {},
                 "monthly": {}}
dailyCurrAccepted = {"daily": [], "daily1": [], "daily2": [], "weekly": [], "monthly": []}
dailyCmdQueue = {34822: {"dtype": "daily", "doubledaily": False}}  # Pending video submissions
submitRecordRatelimits = {34435453: 3600}

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}
bot = interactions.Client()

challenge_names_list, challenge_levels_list = (), ()
modals = {}

lvlsLimit = 300
embedCol2 = 0xfafa00
verifySSL = True  # turn this off if weird stuff happens

listPointRoles = {}
dailyPointRoles = {}


async def updateLevels():
    global lvlsLimit, challenge_names_list, challenge_levels_list
    level_names_list = []
    levels_list = []

    i = 0
    while i <= lvlsLimit:
        r = await requestGET(f"https://challengelist.gd/api/v1/demons/?limit=50&after={i}")
        if not r:
            break
        for level in r:
            levels_list.append(level)
            level_names_list.append(level['name'].lower())
        i += 50

    lvlsLimit = len(level_names_list)
    challenge_names_list = tuple(level_names_list)
    challenge_levels_list = tuple(levels_list)


@bot.event
async def on_ready():
    global dailySubsChannel, dailyQueueChannel, \
        dailyQueueChannelID, dailySubsChannelID, \
        doubleFriday, currDailies, dailyAnnounceChannel

    dailySubsChannel = await interactions.get(client=bot, obj=interactions.GuildChannel, object_id=dailySubsChannelID)
    dailyQueueChannel = await interactions.get(client=bot, obj=interactions.GuildChannel, object_id=dailyQueueChannelID)
    dailyAnnounceChannel = await interactions.get(client=bot, obj=interactions.GuildChannel,
                                                  object_id=dailyAnnounceChannelID)

    await dailyLocalCollect()
    await dChallsCollect()
    await listUsersCollect()

    PList = [25, 50, 100, 250, 500, 750,
             1000, 1500, 2000, 3000, 4000,
             5000, 6000, 7000, 8000, 8402.39]

    roles = await bot.guilds[0].get_all_roles()
    for r in roles:
        for n in PList:
            if r.name == f"{n} Points":
                listPointRoles.update({n: r.id})
            elif r.name == f"{n} Cool-Stars":
                dailyPointRoles.update({n: r.id})

    print(f"Bot online and logged in as {bot.me.name}")

    i = 0
    diff, diffFinal = None, 0
    currDailies = {"daily": await calcCurrDaily("daily"),
                   "monthly": await calcCurrDaily("monthly"),
                   "weekly": await calcCurrDaily("weekly")}
    prevDailies = {"daily": await calcCurrDaily("daily"),
                   "monthly": await calcCurrDaily("monthly"),
                   "weekly": await calcCurrDaily("weekly")}
    await updateLevels()
    while True:
        t1 = datetime.now()
        # print(prevDailies, currDailies)
        await asyncio.sleep(30 - diffFinal)
        doubleFriday = await isFriday()
        currDailies = {"daily": await calcCurrDaily("daily"),
                       "monthly": await calcCurrDaily("monthly"),
                       "weekly": await calcCurrDaily("weekly")}

        for dType in ['daily', 'monthly', 'weekly']:
            if dType == 'daily' and await isFriday() and prevDailies['daily'] != currDailies['daily']:
                dailyCurrAccepted[dType] = []
                await postDaily(dailyAnnounceChannel, 'daily1', currDailies['daily'])
                await postDaily(dailyAnnounceChannel, 'daily2', currDailies['daily'])
            else:
                if currDailies[dType] != prevDailies[dType]:
                    for d in ('daily1', 'daily2', 'daily'):
                        dailyCurrAccepted[d] = []
                    await postDaily(dailyAnnounceChannel, dType, currDailies[dType])
        for k in submitRecordRatelimits.keys():
            submitRecordRatelimits[k] -= 30
        prevDailies = currDailies
        if i % 10 == 0:
            await updateLevels()
            await clearCache()
        t2 = datetime.now()
        diff = t2 - t1
        diffFinal = diff.seconds + diff.microseconds * 0.000001
        i += 1


@interactions.slash_command(name="leaderboard", description="Shows the top 10 players (currently)")
@interactions.slash_option(name="page", description="Leaderboard page to show",
                        opt_type=interactions.OptionType.INTEGER, required=False)
@interactions.slash_option(name="limit", description="Amount of players to show",
                                          opt_type=interactions.OptionType.INTEGER, required=False,
                                          min_value=5, max_value=25)
@interactions.slash_option(name="country", description="Get country leaderboard",
                                          opt_type=interactions.OptionType.STRING, required=False)
async def leaderboard(ctx: interactions.SlashContext, page: int = None, limit: int = 10, country: str = None):
    out = await getLeaderboard(ctx, limit, country, after=(page * limit) if page else None)
    if type(out) == tuple:
        await ctx.send(embeds=out[0], components=out[1] if not out[2] else [out[1], out[2]])
    else:
        return


@interactions.component_callback("backpage_leaderboard")
async def backpage_leaderboard(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    title = ctx.message.embeds[0].title
    country, after, limit = await leaderboardDetails(title)
    after -= limit

    out = await getLeaderboard(ctx, limit, country, after=after, autocorrect=False)
    await ctx.edit(content="", embeds=out[0], components=[out[1], out[2]])


@interactions.component_callback("nextpage_leaderboard")
async def nextpage_leaderboard(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    title = ctx.message.embeds[0].title
    country, after, limit = await leaderboardDetails(title)
    after += limit

    out = await getLeaderboard(ctx, limit, country, after=after, autocorrect=False)
    await ctx.edit(content="", embeds=out[0], components=[out[1], out[2]])


@interactions.component_callback("leaderboard_playermenu")
async def leaderboard_playersel(ctx: interactions.ComponentContext, val):
    if not await checkInteractionPerms(ctx): return
    out = await getProfile(ctx, name=val[0].split("_")[2], completionLinks=False, embedCol=embedCol2)
    if out:
        await ctx.edit(content="", embeds=[ctx.message.embeds[0], out], components=ctx.message.components)


@interactions.component_callback("countrycorrect")
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


@interactions.slash_command(name="challenges", description="Shows the top challenges")
@interactions.slash_option(name="limit", description="How many challenges to show (limit is 25)",
                                          opt_type=interactions.OptionType.INTEGER, required=False, min_value=5,
                                          max_value=25)
@interactions.slash_option(name="page",
                                          description="Challenges page (depends on limit parameter if provided)",
                                          opt_type=interactions.OptionType.INTEGER, required=False)
async def challenges(ctx: interactions.SlashContext, limit: int = 10, page: int = None):
    title = await getChallsTitle(limit, page=page)
    embed = await getChallenges(ctx, limit, 0 if not page else page * limit, title,
                                challenges_list=challenge_levels_list if challenge_levels_list else None)
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
    actionRow = interactions.ActionRow(back_button, move_button)
    await ctx.send(embeds=[embed[0]], components=[actionRow, embed[1]])


@interactions.component_callback("getchallenges_menu")
async def getchallenges_menusel(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    pos = int(ctx.values[0].split("_")[1])
    origEmbed = ctx.message.embeds[0]
    origComponents = ctx.message.components

    embed = await showChallenge(ctx, lvl_pos=pos, challenge_names=challenge_names_list, embedCol=embedCol2)
    await ctx.edit(content="", embeds=[origEmbed, embed], components=origComponents)


@interactions.component_callback("nextpage_challenges")
async def challenges_nextpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return

    desc = ctx.message.embeds[0].description
    limit, after, title = await getLinkInfo(await getSubstr(desc, "(", ")"))
    after += limit
    title = await getChallsTitle(limit, after=after)
    embed = await getChallenges(ctx, limit, after, title,
                                challenges_list=challenge_levels_list if challenge_levels_list else None)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled=False if limit * 2 + after <= lvlsLimit else True
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled=False if ((after - limit) >= 0) else True
    )
    actionRow = interactions.ActionRow(back_button, move_button)
    await ctx.edit(embeds=[embed[0]], components=[actionRow, embed[1]])


@interactions.component_callback("backpage_challenges")
async def challenges_backpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return

    desc = ctx.message.embeds[0].description
    limit, after, title = await getLinkInfo(await getSubstr(desc, "(", ")"))
    after -= limit
    title = await getChallsTitle(limit, after=after)
    embed = await getChallenges(ctx, limit, after, title,
                                challenges_list=challenge_levels_list if challenge_levels_list else None)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.SUCCESS,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled=False if limit * 2 + after <= lvlsLimit else True
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled=False if ((after - limit) >= 0) else True
    )
    actionRow = interactions.ActionRow(components=[back_button, move_button])
    await ctx.edit(embeds=[embed[0]], components=[actionRow, embed[1]])


@interactions.slash_command(name="profile", description="Lookup a player's rank/demons beaten/etc.")
@interactions.slash_option(name="name", description="Player's name", opt_type=interactions.OptionType.STRING,
                                          required=False)
@interactions.slash_option(name="discord_user", description="Discord user to get profile of",
                                          opt_type=interactions.OptionType.USER,
                                          required=False)
async def profile(ctx: interactions.SlashContext, name: str = None, discord_user: interactions.User = None):
    # SELECT * FROM users
    # WHERE discord_id = {ctx.user.id};
    out = await getProfile(ctx, name=name, discUser=discord_user, completionLinks=True)
    if out:
        await ctx.send(embeds=out[0], components=list(out[1]) if out[1] else None)


@interactions.slash_command(name="submitrecord", description="Submit a challenge record to the list")
async def submitrecord(ctx: interactions.SlashContext):
    field_challenge = interactions.InputText(
        style=interactions.TextStyles.SHORT, label="Challenge (leave blank for \" \")",
        custom_id="submitrecord_challenge",
        min_length=1, required=False)
    field_player = interactions.InputText(
        style=interactions.TextStyles.SHORT, label="Player name", custom_id="submitrecord_player",
        min_length=1, required=True)

    field_video = interactions.InputText(
        style=interactions.TextStyles.SHORT, label="Video link (youtube, bilibili, etc.)",
        custom_id="submitrecord_video",
        min_length=10, required=True)

    field_rawfootage = interactions.InputText(
        style=interactions.TextStyles.SHORT, label="Raw footage link", custom_id="submitrecord_rawfootage",
        min_length=10, required=True)

    field_note = interactions.InputText(
        style=interactions.TextStyles.SHORT, label="Note (optional)", custom_id="submitrecord_note",
        min_length=1, required=False)

    modal = interactions.Modal(field_challenge, field_player, field_video, field_rawfootage, field_note, title="Submit List Completion Form", custom_id="modal_submitrecord")
    await ctx.send_modal(modal)


@interactions.modal_callback("modal_submitrecord")
async def submitrecord_confirmation(ctx: interactions.ComponentContext, challenge, player, video, raw_footage, note):
    modals.update({int(ctx.user.id): (challenge, player, video, raw_footage, note)})
    cLevel = await correctLevel(ctx, challenge, challenge_names_list)
    if not cLevel:
        await ctx.send(
            content=f"<@{ctx.user.id}>, the level you submitted a completion for cannot be found. Please check the name and try again.",
            ephemeral=True)
        return
    if type(cLevel) == tuple:
        await ctx.send(embed=cLevel[0], components=cLevel[1:])
        return

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


@interactions.component_callback("submitrecord_autocorrect")
async def submitrecord_autocorrect(ctx: interactions.ComponentContext):
    modal_data = modals[ctx.user.id]
    challenge, player, video, raw_footage, note = modal_data

    embed = interactions.Embed(title="List Completion Confirmation",
                               description=f"<@{ctx.user.id}>, please review the details you submitted for your list completion:")
    for detail in (("Challenge", challenge if challenge else "\" \""), ("Player", player), ("Video link", video),
                   ("Raw footage link", raw_footage), ("Note", note if note else "None")):
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


@interactions.component_callback("submitrecord_cancel")
async def submitecord_cancel(ctx: interactions.ComponentContext):
    await ctx.send("**List completion submission cancelled.**")


@interactions.component_callback("submitrecord_confirm")
async def submitrecord_confirmed(ctx: interactions.ComponentContext):
    embed = ctx.message.embeds[0]
    challenge = embed.fields[0].value
    player = embed.fields[1].value
    video = embed.fields[2].value
    raw_footage = embed.fields[3].value
    note = embed.fields[4].value if embed.fields[4].value != "None" else None
    try:
        # find ID
        if challenge != "\" \"":
            demon_id = 249  # the exception
        else:
            demon_id = \
                (await requestGET(f"https://challengelist.gd/api/v1/records/demons/?name_contains={challenge}"))[0][
                    "id"]

        await requestPOST(session, "https://challengelist.gd/api/v1/records/",
                          data={"demon": demon_id, "player": player, "video": video,
                                "raw_footage": raw_footage,
                                "note": (
                                        note + f" (Requested with CLBot by {ctx.author.user.username}#{ctx.author.user.discriminator} / {int(ctx.author.user.id)})") if note
                                else f"Requested with CLBot by {ctx.author.user.username}#{ctx.author.user.discriminator} / {int(ctx.author.user.id)}",
                                "progress": 100})
        await ctx.send(f"**<@{ctx.user.id}>**, record sent successfully!**")
    except Exception as e:
        await ctx.send(embeds=(await errorEmbed(e)))


@interactions.slash_command(name="getchallenge",
             description="Lookup completions of a challenge (make sure to use one of the two options)")
@interactions.slash_option(name="level", description="Level name (not case-sensitive)",
                                          opt_type=interactions.OptionType.STRING, required=False)
@interactions.slash_option(name="position", description="List position",
                                          opt_type=interactions.OptionType.INTEGER, required=False)
async def getchallenge(ctx: interactions.SlashContext, level: str = None, position: int = None):
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
            buttons = await getChallButtons(lvlsLimit, pos)
            await ctx.send(embeds=out[0], components=buttons)
    else:
        out = await showChallenge(ctx, lvl_pos=position)
        buttons = await getChallButtons(lvlsLimit, position)
        await ctx.send(embeds=out, components=buttons)


@interactions.component_callback("levelcorrect")
async def levelcorrect(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx):
        return
    lvl = ctx.component.label
    embed, pos = await showChallenge(ctx, lvl_name=lvl)
    lastDemon, nextDemon = await getChallButtons(lvlsLimit, pos)
    await ctx.edit(embed=embed, components=[lastDemon, nextDemon])


@interactions.component_callback("next_demon")
async def nextchallenge(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    pos = int(await getSubstr(ctx.message.embeds[0].title, "#", ".")) + 1
    embed = await showChallenge(ctx, lvl_pos=pos)
    buttons = await getChallButtons(lvlsLimit, pos)
    await ctx.edit(content="", embeds=embed, components=buttons)


@interactions.component_callback("back_demon")
async def backchallenge(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    pos = int(ctx.message.embeds[0].title.split("#")[1].split(".")[0]) - 1
    embed = await showChallenge(ctx, lvl_pos=pos)
    buttons = await getChallButtons(lvlsLimit, pos)
    await ctx.edit(content="", embeds=embed, components=buttons)


@interactions.component_callback("completions_menu")
async def completions_menusel(ctx: interactions.ComponentContext, val):
    if not await checkInteractionPerms(ctx):
        return

    await ctx.send(embeds=(await showCompletion(val[0])), ephemeral=True)


@interactions.component_callback("backpage_completions")
async def completions_backpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx):
        return
    embed = ctx.message.embeds[0]
    player = embed.title.split(" :")[0]
    currPage = int(await getSubstr(ctx.message.components[0].components[0].placeholder, "(", "/"))
    out = await getProfile(ctx, name=player, completionLinks=True, completionsPage=currPage - 1)
    await ctx.edit(embeds=out[0], components=out[1])


@interactions.component_callback("nextpage_completions")
async def completions_nextpage(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx):
        return
    embed = ctx.message.embeds[0]
    player = embed.title.split(" :")[0]
    currPage = int(await getSubstr(ctx.message.components[0].components[0].placeholder, "(", "/"))

    out = await getProfile(ctx, name=player, completionLinks=True, completionsPage=currPage + 1)
    await ctx.edit(embeds=out[0], components=out[1])

# use cases here
@interactions.component_callback("levelcorrect0")
async def autocorrect_challenge(ctx: interactions.ComponentContext):
    pos = int(await getSubstr(ctx.component.label, "#", ")"))
    embed = await showChallenge(ctx, lvl_pos=pos)
    lastDemon, nextDemon = await getChallButtons(lvlsLimit, pos)
    await ctx.edit(embeds=embed, components=[lastDemon, nextDemon])


# == DAILY FEATURES ==

@interactions.component_callback("daily_rejectsub")
async def daily_rejectcompletion(ctx: interactions.ComponentContext):
    dailynum, dType, doubleDaily, dms = await getDailyDetails(ctx.message.content, bot, token, getUser=False)
    mTitle = f"{dType} Completion #{dailynum} Rejection Form"
    modal = interactions.Modal(interactions.InputText(style=interactions.TextStyles.SHORT,
                                                                  label="Reason", custom_id="reason", min_length=3,
                                                                  required=True),
                               title=mTitle, custom_id="daily_rejectmodal",)
    await ctx.send_modal(modal=modal)


@interactions.modal_callback("daily_rejectmodal")
async def daily_rejectconf(ctx: interactions.ComponentContext, reason):
    dailynum, dType, doubleDaily, dms, user = await getDailyDetails(ctx.message.content, bot, token)
    dKey = dType.lower() if not doubleDaily else f"daily{doubleDaily}"
    if int(user.id) in dailyCurrSubs[dKey].keys():  # get rid of the completion in queue
        dailyCurrSubs[dKey].pop(int(user.id))
    if dms:
        await user.send(
            f"Your submission for {dType} #{dailynum} was unfortunately rejected by <@{ctx.user.id}> for reason: `{reason}`. Please contact them and/or try submitting your completion again."
            if doubleDaily else f"Your double daily #{dailynum} submission was unfortunately rejected by <@{ctx.user.id}> for reason: `{reason}`. Please contact them and/or try submitting your completion again.")
    await ctx.message.delete()


@interactions.component_callback("daily_acceptsub")
async def daily_acceptcompletion(ctx: interactions.ComponentContext):
    dailynum, dType, doubleDaily, dms = await getDailyDetails(ctx.message.content, bot, token, getUser=False)
    modal = interactions.Modal(interactions.InputText(style=interactions.TextStyles.SHORT,
                                                                  label="Confirmation: don't type anything here!",
                                                                  custom_id="confirmation", min_length=4,
                                                                  required=False),
                               title=f"{dType} Completion #{dailynum} Acceptance", custom_id="daily_acceptmodal")
    await ctx.send_modal(modal=modal)


@interactions.modal_callback("daily_acceptmodal")
async def daily_acceptconf(ctx: interactions.ComponentContext, confirmation=None):
    # ^ don't use the `confirmation` parameter, this is just needed to be passed as an argument by
    # the library when the modal confirmation button is clicked on
    dailynum, dType, doubleDaily, dms, user = await getDailyDetails(ctx.message.content, bot, token)
    dKey = dType.lower() if not doubleDaily else f"daily{doubleDaily}"
    if int(user.id) in dailyCurrSubs[dKey].keys():
        dailyCurrSubs[dKey].pop(int(user.id))
        dailyCurrAccepted[dKey].append(int(user.id))

    dailyPts = await getDailyPoints(dKey, dailynum)
    p = await addPoints(int(user.id), dailyPts, showEmbed=False)
    if p:
        await ctx.send(embeds=p)
        return
    if dms:
        await user.send(f"Your submission for {dType} #{dailynum} was accepted!" if doubleDaily else
                        f"Your double daily #{dailynum} submission was accepted!")
    await ctx.message.delete()


@interactions.component_callback("daily_subnotes")
async def daily_compnotes(ctx: interactions.ComponentContext):
    modal = interactions.Modal(title=f"Add Notes For Completion", custom_id="daily_subnotescomp",
                               components=[interactions.InputText(style=interactions.TextStyles.SHORT,
                                                                  label="Completion Notes",
                                                                  custom_id="compnotes", min_length=4,
                                                                  required=True)])
    await ctx.send_modal(modal=modal)


@interactions.modal_callback("daily_subnotescomp")
async def daily_subnotescomp(ctx: interactions.ComponentContext, compnotes: str):
    msg = ctx.message
    if "Staff Notes" in msg.content:
        mParsed = msg.content.split("\n")
        mParsed[len(mParsed) - 1] = "**Staff Notes**: " + compnotes
        nMessage = "\n".join(mParsed)
    else:
        nMessage = msg.content + "\n**Staff Notes**: " + compnotes
    await ctx.send(content=nMessage, components=[dailyRejectButton, dailyAcceptButton, dailyNotesButton])
    await msg.delete()


@interactions.slash_command(name="daily_sendcomp", description="Send a daily completion")
@interactions.slash_option(name="dtype",
                                          description="Is your submission for a daily, weekly or monthly?",
                                          opt_type=interactions.OptionType.STRING,
                                          required=True,
                                          choices=[
                                              interactions.SlashCommandChoice(name="Daily", value="daily"),
                                              interactions.SlashCommandChoice(name="Weekly", value="weekly"),
                                              interactions.SlashCommandChoice(name="Monthly", value="monthly"),
                                              interactions.SlashCommandChoice(name="Double Daily Friday #1", value="daily1"),
                                              interactions.SlashCommandChoice(name="Double Daily Friday #2", value="daily2")
                                          ])
@interactions.slash_option(name="video", description="Completion video",
                                          opt_type=interactions.OptionType.ATTACHMENT, required=True)
@interactions.slash_option(name="notes", description="Additional completion notes",
                                          opt_type=interactions.OptionType.STRING, required=False)
@interactions.slash_option(name="direct_message",
                                          description="Set to True if you want to be DMed on acceptance or rejection, set to False otherwise",
                                          opt_type=interactions.OptionType.BOOLEAN, required=False)
async def daily_submitcompletion(ctx: interactions.SlashContext, dtype: str, video: interactions.Attachment, notes: str = None,
                                 direct_message: bool = False):
    userID = int(ctx.user.id)
    doubledaily = dtype[5] if "1" in dtype or "2" in dtype else False

    if (doubledaily and not doubleFriday) or (doubledaily and dtype != "daily"):
        await ctx.send("Today is not Double Daily Friday/your submission is not for a double daily!")
        return
    if userID in dailyCurrSubs[dtype] or userID in dailyCurrAccepted[dtype]:
        await ctx.send(f"You have already submitted a {dtype} submission/it has already been accepted!")
        return
    if doubleFriday and not doubledaily and dtype == "daily":
        await ctx.send(f"Today is Double Daily Friday, please pick one of the Double Dailies!")
        return

    if "video" not in video.content_type:
        await ctx.send("Your submission must be in video form!")
        return

    dKey = dtype if not doubledaily else doubledaily
    user_video = await video.download()

    msg = f"## __{dtype.capitalize()} #{currDailies[dtype]} Submission__" + (
        "" if not doubledaily else f" (DDF #{doubledaily[5]})")
    msg += f"\n**User:** <@{userID}>\n**Player Notes:** {notes}"
    dMsg = await dailyQueueChannel.send(content=msg,
                                        components=[dailyAcceptButton, dailyRejectButton, dailyNotesButton],
                                        files=[interactions.File(video.filename, fp=user_video)])
    dailyCurrSubs[dKey].update({userID: dMsg})
    await ctx.send(
        f"{dtype.capitalize()} #{currDailies[dtype]} completion submitted! Please wait a couple days for daily managers to review your submission.")
    # dailyCmdQueue.update({userID: {"dtype": dtype, "doubledaily": doubledaily, "notes": notes, "dms": direct_message}})
    # await ctx.send("Please reply to this message with **a video** of your completion.")


@interactions.slash_command(name="daily_cancelcomp", description="Cancel your daily submission.")
@interactions.slash_option(name="dtype",
                                          description="Was your submission for a daily, weekly or monthly?",
                                          opt_type=interactions.OptionType.STRING,
                                          required=True,
                                          choices=[
                                              interactions.SlashCommandChoice(name="Daily", value="daily"),
                                              interactions.SlashCommandChoice(name="Weekly", value="weekly"),
                                              interactions.SlashCommandChoice(name="Monthly", value="monthly")
                                          ])
@interactions.slash_option(name="doubledaily",
                                          description="If the submission was meant for double daily friday, which daily?",
                                          opt_type=interactions.OptionType.STRING,
                                          required=False,
                                          choices=[
                                              interactions.SlashCommandChoice(name="Daily #1", value="daily1"),
                                              interactions.SlashCommandChoice(name="Daily #2", value="daily2")
                                          ])
async def daily_cancelcomp(ctx: interactions.SlashContext, dtype: str, doubledaily: str = None):
    userID = int(ctx.user.id)
    dKey = doubledaily if doubledaily else dtype
    if not int(ctx.user.id) in dailyCurrSubs[dKey]:
        dailyname = f"Double Daily #{doubledaily[5]}" if doubledaily else f"a {dtype}"
        await ctx.send(f"You have not sent a completion for {dailyname}/it has already been accepted!")
    else:
        await dailyCurrSubs[dKey][userID].delete(reason="Submission cancelled")
        dailyCurrSubs[dKey].pop(userID)
        await ctx.send(f"Submission cancelled.")


@interactions.slash_command(name="senddaily", description="send daily")
@interactions.slash_option(name="dailytype", opt_type=interactions.OptionType.STRING, required=True, description="Daily ID",
                        choices=[
                            interactions.SlashCommandChoice(name="Daily", value="daily"),
                            interactions.SlashCommandChoice(name="Weekly", value="weekly"),
                            interactions.SlashCommandChoice(name="Monthly", value="monthly"),
                            interactions.SlashCommandChoice(name="DDF #1", value="daily1"),
                            interactions.SlashCommandChoice(name="DDF #2", value="daily2"),
                        ])
@interactions.slash_option(name="dailynum", opt_type=interactions.OptionType.INTEGER, required=True, description="Channel")
async def postdaily(ctx, dailytype, dailynum):
    await postDaily(dailyAnnounceChannel, dailytype, dailynum)
    await ctx.send("Sent!")


@interactions.slash_command(name="daily_addpoints", description="Add points")
@interactions.slash_option(name="duser", opt_type=interactions.OptionType.USER, required=True, description="Daily user")
@interactions.slash_option(name="points", opt_type=interactions.OptionType.INTEGER, required=True, description="Points to add")
async def daily_addpoints(ctx: interactions.SlashContext, duser: interactions.User, points: int):
    pts = await addPoints(int(duser.id), points)
    await ctx.send(embeds=pts)


@interactions.slash_command(name="daily_setpoints", description="Set points")
@interactions.slash_option(name="user", opt_type=interactions.OptionType.USER, required=True, description="Daily user")
@interactions.slash_option(name="points", opt_type=interactions.OptionType.INTEGER, required=True, description="Points to set")
async def daily_setpoints(ctx: interactions.SlashContext, user: interactions.User, points: int):
    pts = await setPoints(int(user.id), points)
    await ctx.send(embeds=pts)


@interactions.slash_command(name="daily_points", description="View a player's daily points")
@interactions.slash_option(name="user", opt_type=interactions.OptionType.USER, required=False, description="Daily user")
async def daily_points(ctx: interactions.SlashContext, user: interactions.User = None):
    if user:
        uid = user.id
    else:
        uid = ctx.user.id

    ptsEmbed = await getPoints(int(uid))
    await ctx.send(embeds=ptsEmbed)


@interactions.slash_command(name="daily_addchall", description="Add a daily challenge")
@interactions.slash_option(name="dailytype", opt_type=interactions.OptionType.STRING, required=True, description="Daily type",
                        choices=[
                            interactions.SlashCommandChoice(name="Daily", value="daily"),
                            interactions.SlashCommandChoice(name="Weekly", value="weekly"),
                            interactions.SlashCommandChoice(name="Monthly", value="monthly"),
                            interactions.SlashCommandChoice(name="DDF #1", value="daily1"),
                            interactions.SlashCommandChoice(name="DDF #2", value="daily2"),
                        ])
@interactions.slash_option(name="dailynum", opt_type=interactions.OptionType.INTEGER, required=True,
                        description="Daily number")
@interactions.slash_option(name="dailyid", opt_type=interactions.OptionType.INTEGER, required=True, description="Daily ID")
@interactions.slash_option(name="coolstars", opt_type=interactions.OptionType.INTEGER, required=True,
                        description="cool stars")
async def add_daily(ctx: interactions.SlashContext, dailytype: str, dailynum: int, dailyid: int, coolstars: int):
    op = await addDaily(str(ctx.user.id), str(dailyid), dailytype, dailynum, coolstars)
    await ctx.send(embeds=op)


@interactions.slash_command(name="daily_setnextchall", description="Set the next daily challenge")
@interactions.slash_option(name="dailytype", opt_type=interactions.OptionType.STRING, required=True, description="Daily type",
                        choices=[
                            interactions.SlashCommandChoice(name="Daily", value="daily"),
                            interactions.SlashCommandChoice(name="Weekly", value="weekly"),
                            interactions.SlashCommandChoice(name="Monthly", value="monthly"),
                            interactions.SlashCommandChoice(name="DDF #1", value="daily1"),
                            interactions.SlashCommandChoice(name="DDF #2", value="daily2"),
                        ])
@interactions.slash_option(name="dailyid", opt_type=interactions.OptionType.INTEGER, required=True, description="Daily ID")
@interactions.slash_option(name="coolstars", opt_type=interactions.OptionType.INTEGER, required=True,
                        description="cool stars")
async def add_nextdaily(ctx: interactions.SlashContext, dailytype: str, dailyid: int, coolstars: int):
    op = await addDaily(str(ctx.user.id), str(dailyid), dailytype, currDailies[dailytype] + 1, coolstars)
    await ctx.send(embeds=op)


@interactions.slash_command(name="daily_currdailies", description="Show current dailies")
async def daily_nums(ctx: interactions.SlashContext):
    embedDesc = ""
    for dtype in ["daily", "weekly", "monthly"]:
        inf = await getDailyInfo(dtype, currDailies[dtype])
        embedDesc += f"**{dtype.capitalize()}: ** #{currDailies[dtype]} {inf}\n"
    embed = interactions.Embed(title="Current Dailies", description=embedDesc)
    await ctx.send(embeds=embed)


@interactions.slash_command(name="daily_editchall", description="Edit a daily challenge")
@interactions.slash_option(name="dailytype", opt_type=interactions.OptionType.STRING, required=True, description="Daily ID",
                        choices=[
                            interactions.SlashCommandChoice(name="Daily", value="daily"),
                            interactions.SlashCommandChoice(name="Weekly", value="weekly"),
                            interactions.SlashCommandChoice(name="Monthly", value="monthly"),
                            interactions.SlashCommandChoice(name="DDF #1", value="daily1"),
                            interactions.SlashCommandChoice(name="DDF #2", value="daily2"),
                        ])
@interactions.slash_option(name="dailynum", opt_type=interactions.OptionType.INTEGER, required=True,
                        description="Daily number")
@interactions.slash_option(name="dailyid", opt_type=interactions.OptionType.INTEGER, required=False, description="Daily ID")
@interactions.slash_option(name="coolstars", opt_type=interactions.OptionType.INTEGER, required=False,
                        description="cool stars")
async def edit_daily(ctx: interactions.SlashContext, dailytype: str, dailynum: int, dailyid=None, coolstars=None):
    editDict = {}
    if dailyid:
        name, creator = await levelDetails(dailyid)
        editDict.update({"level_id": str(dailyid)})
        editDict.update({"name": name})
        editDict.update({"creator": creator})
    if coolstars:
        editDict.update({"stars": coolstars})
    op = await editDaily(dailytype, dailynum, editDict)
    await ctx.send(embeds=op)


@interactions.slash_command(name="daily_leaderboard", description="View daily leaderboard")
@interactions.slash_option(name="page", opt_type=interactions.OptionType.INTEGER, required=False,
                                          description="Leaderboard page",
                                          min_value=1, max_value=230)
@interactions.slash_option(name="limit", opt_type=interactions.OptionType.INTEGER, required=False,
                                          description="Limit of players",
                                          min_value=5, max_value=20)
async def daily_leaderboard(ctx: interactions.SlashContext, page: int = 1, limit: int = 10):
    embed, backButton, nextButton = await dailyLeaderboard(ctx, page, limit)
    await ctx.send(embeds=embed, components=[backButton, nextButton])


@interactions.component_callback("dleaderboard_back")
async def dailyLeaderboardBack(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    page, limit = await dLeaderboardDetails(ctx.message.embeds[0].title)
    page -= 1
    embed, backButton, nextButton = await dailyLeaderboard(ctx, page, limit)
    await ctx.edit(embeds=embed, components=[backButton, nextButton])


@interactions.component_callback("dleaderboard_next")
async def dailyLeaderboardNext(ctx: interactions.ComponentContext):
    if not await checkInteractionPerms(ctx): return
    page, limit = await dLeaderboardDetails(ctx.message.embeds[0].title)
    page += 1
    embed, backButton, nextButton = await dailyLeaderboard(ctx, page, limit)
    await ctx.edit(embeds=embed, components=[backButton, nextButton])


@interactions.slash_command(name="updateroles", description="Update your cool stars, list points, etc. roles with this command")
async def updateRoles(ctx: interactions.SlashContext):
    d = await ctx.send("Updating roles...")
    userId = int(ctx.user.id)
    dCurrPoints = await getPointsInt(userId)
    lCurrPoints = await discToListPoints(str(userId))

    # contact ultimatepro64lol@gmail.com for more information
    rolesToUpdate = []
    for lP in [100, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 8402.39]:
        if lCurrPoints >= lP:
            rolesToUpdate.append(listPointRoles[lP])
        else:
            break
    for dP in [25, 50, 100, 250, 500, 750, 1000, 1500, 2000, 3000, 4000, 5000]:
        if dCurrPoints >= dP:
            rolesToUpdate.append(dailyPointRoles[dP])
        else:
            break

    updatedRolesList = []
    for role in rolesToUpdate:
        if role not in ctx.member.roles:
            await ctx.member.add_role(listPointRoles[lP])
            updatedRolesList.append(role)

    rolesList = ""
    for rID in updatedRolesList:
        rolesList += f"<@&{rID}> "
    if not rolesList:
        embed = await successEmbed("No new roles added.")
    else:
        embed = await successEmbed("Added role(s): " + rolesList)

    await d.delete()
    await ctx.send(embeds=embed, content="")


@interactions.slash_command(name="linkdiscord", description="Link a user's discord account to their Challenge List account")
@interactions.slash_option(name="user", opt_type=interactions.OptionType.USER, required=True,
                                          description="Daily user")
@interactions.slash_option(name="name", opt_type=interactions.OptionType.STRING, required=True,
                                          description="Name of account to link")
async def linkdiscord(ctx: interactions.SlashContext, user: interactions.User, name: str):
    embed = await lLinkAccount(str(user.id), name)
    await ctx.send(embeds=embed)


@interactions.slash_command(name="unlinkdiscord",
             description="Unlink a user's discord account from their previous Challenge List account")
@interactions.slash_option(name="user", opt_type=interactions.OptionType.USER, required=True,
                                          description="Daily user")
async def unlinkdiscord(ctx: interactions.SlashContext, user: interactions.User):
    embed = await lUnlinkAccount(str(user.id))
    await ctx.send(embeds=embed)


bot.start("ODYxMzU4ODIxMzM0NTgxMjY5.G2SZi9.G21dYVgQbqM0pKzZLVujLLqiRrGb2pXT1n3P8U")
