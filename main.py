import requests
import interactions
import discord
from json import loads as to_json
from json import load
from discord.ext import commands
from utils import *
import functools
import pymysql
import mysql.connector
from mysql.connector import Error
import asyncio
from datetime import datetime

createdAt = (datetime.now() - datetime(1970, 1, 1)).total_seconds()

token = load(open("token.json"))['token']

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}

sql_creds = load(open("sql_creds.json"))
activity = interactions.PresenceActivity(name="VSC",
                                         type=interactions.PresenceActivityType.GAME, created_at=createdAt)
presence = interactions.ClientPresence(activities=[activity])

bot = interactions.Client(token=token, presence=presence)



sql_connection = create_connection(sql_creds['host'], sql_creds['database'], sql_creds['username'], sql_creds['password'])

challenge_names_list = ()
async def updateLevels():
    global challenge_names_list
    levels_list = []
    i = 0
    while i <= 300:
        r = to_json(requests.get(f"https://challengelist.gd/api/v1/demons/?limit=50&after={i}", headers=headers).text)
        #print(r)
        for level in r:
            levels_list.append(level['name'].lower())
            #print(level['name'])
        i += 50
    challenge_names_list = tuple(levels_list)
    print("Reloaded challenges")

@bot.event
async def on_ready():
    await updateLevels()
    print(f"Bot online and logged in as {bot} in guilds {bot.guilds}")
    while True:
        await asyncio.sleep(300)
        await updateLevels() # update levels

# @bot.command(name="linkdiscord", description="Link your discord to your Challenge List profile!",
#              options=[interactions.Option(name="username", description="Challenge list username", type=interactions.OptionType.STRING, required=True)])
# async def linkdiscord(ctx: interactions.CommandContext, username: str):
#     r = await sql_query(sql_connection,
#                         f"SELECT * from users WHERE discord_id = '{int(ctx.user.id)}';")
#     if r is None:
#         r = await sql_query(sql_connection, f"INSERT INTO users (discord_id, user) VALUES ('{int(ctx.user.id)}', '{username}');")
#         await ctx.send(f"<@{int(ctx.user.id)}>, your Discord account was linked successfully!")
#     else:
#         await ctx.send(f"<@{int(ctx.user.id)}>, your Discord account is already linked!")

@bot.command(name="leaderboard", description="Shows the top 10 players (currently)",
             options=[interactions.Option(name="page", description="Leaderboard page to show", type=interactions.OptionType.INTEGER, required=False),
                      interactions.Option(name="limit", description="Amount of players to show", type=interactions.OptionType.INTEGER, required=False,
                                          min_value=5, max_value=25, value=10),
                      interactions.Option(name="country", description="Get country leaderboard", type=interactions.OptionType.STRING, required=False)])
async def leaderboard(ctx: interactions.CommandContext, page: int = None, limit: int = None, country: str = None):
    if page:
        out = await getLeaderboard(ctx, limit, country, after=page * (limit if limit else 10))
    else:
        out = await getLeaderboard(ctx, limit, country)
    if type(out) == tuple:
        if len(out) == 3:
            await ctx.send(embeds=out[0], components=[out[1], out[2]])
        else:
            await ctx.send(embeds=out[0], components=[out[1], out[2], out[3]])
    else:
        return

@bot.component("backpage_leaderboard")
async def backpage_leaderboard(ctx: interactions.CommandContext):
    d = await ctx.defer(edit_origin=True)
    title = ctx.message.embeds[0].title
    limit = 10
    after = 0
    country = None
    if "in" in title:
        country = title[title.index("in") + 3: title.index(")")]
        if "Top" in title:
            # Challenge List Leaderboard (Top 10 in Argentina)
            limit = int(title.split("Top ")[1].split(" ")[0])
        else:
            # Challenge List Leaderboard (#11-20 in Argentina)
            after = int(title.split("#")[1].split("-")[0]) - 1
            limit = int(title.split("-")[1].split(" ")[0]) - after
    else:
        if "Top" in title:
            # Challenge List Leaderboard (Top 10)
            limit = int(title.split("Top ")[1].split(")")[0])
        else:
            # Challenge List Leaderboard (#11-20)
            after = int(title.split("#")[1].split("-")[0]) - 1
            limit = int(title.split("-")[1].split(")")[0]) - after
    after -= limit

    out = await getLeaderboard(ctx, limit, country, after=after, autocorrect=False)
    print(out)
    await d.edit(content="", embeds=out[0], components=[out[1], out[2]])

@bot.component("nextpage_leaderboard")
async def nextpage_leaderboard(ctx: interactions.ComponentContext):
    d = await ctx.defer(edit_origin=True)
    title = ctx.message.embeds[0].title
    limit = 10
    after = 0
    country = None
    if "in" in title:
        country = title[title.index("in") + 3: title.index(")")]
        if "Top" in title:
            # Challenge List Leaderboard (Top 10 in Argentina)
            limit = int(title.split("Top ")[1].split(" ")[0])
        else:
            # Challenge List Leaderboard (#11-20 in Argentina)
            after = int(title.split("#")[1].split("-")[0]) - 1
            limit = int(title.split("-")[1].split(" ")[0]) - after
    else:
        if "Top" in title:
            # Challenge List Leaderboard (Top 10)
            limit = int(title.split("Top ")[1].split(")")[0])
        else:
            # Challenge List Leaderboard (#11-20)
            after = int(title.split("#")[1].split("-")[0]) - 1
            limit = int(title.split("-")[1].split(")")[0]) - after
    after += limit

    out = await getLeaderboard(ctx, limit, country, after=after, autocorrect=False)
    await d.edit(content="", embeds=out[0], components=[out[1], out[2]])

@bot.component("leaderboard_playermenu")
async def leaderboard_playersel(ctx: interactions.ComponentContext, val):
    d = await ctx.defer(edit_origin=True)
    out = await getProfile(ctx, val[0].split("_")[2])
    print(val)
    if out:
        await d.edit(content="", embeds=[ctx.message.embeds[0], out], components=ctx.message.components)

@bot.component("countrycorrect")
async def countrycorrect_button(ctx: interactions.ComponentContext):
    if int(ctx.user.id) != int(ctx.message.embeds[0].split("@")[1].split(">")[0]):
        await ctx.send("This is not your command.", ephemeral=True)
        return

    limit = ctx.message.embeds[0].title.split()[3][:-1]
    cCountry = ctx.component.label
    print(cCountry, limit)
    embed = await getLeaderboard(ctx, int(limit), cCountry, 0, autocorrect=False)

    after = 0
    move_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
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
    if not limit or limit > 25:
        limit = 10

    title = f"Challenge List (Top {limit})"
    embed = await getChallenges(limit, 0 if not page else page * limit, title)
    if not embed:
        await ctx.send("**Error:** Page does not exist!")
    move_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
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
    await ctx.send(embeds=[embed], components=[back_button, move_button])

@bot.component("nextpage_challenges")
async def challenges_nextpage(ctx: interactions.CommandContext):
    embed = ctx.message.embeds[0]
    title = embed.title
    limit = 25
    if "-" in title:
        # (#11-20)
        after = int(embed.fields[0].name.split("**")[1].split(".")[0]) - 1
        limit = int( title.split("-")[1].split(")")[0] ) - after
        # after = 10
        # limit = 10
        after += limit

    else:
        limit = int(title.split(")")[0].split("Top ")[1])
        after = limit
    title = f"Challenge List (#{after + 1}-{after + limit})"

    embed = await getChallenges(limit, after, title)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled = False if limit*2 + after <= 250 else True
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled = False if ((after - limit) >= 0) else True
    )
    await ctx.edit(content="", embeds=[embed], components=[back_button, move_button])

@bot.component("backpage_challenges")
async def challenges_backpage(ctx: interactions.CommandContext):
    embed = ctx.message.embeds[0]
    title = embed.title
    after = int(embed.fields[0].name.split("**")[1].split(".")[0]) - 1
    limit = int(title.split("-")[1].split(")")[0]) - after
    # after = 10
    # limit = 10
    after -= limit
    title = f"Challenge List (#{after + 1}-{after + limit})" if after > 0 else f"Challenge List (Top {limit})"

    embed = await getChallenges(limit, after, title)

    move_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next Page",
        custom_id="nextpage_challenges",
        disabled=False if limit*2 + after <= 250 else True
    )
    back_button = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Last Page",
        custom_id="backpage_challenges",
        disabled=False if ((after - limit) >= 0) else True
    )
    await ctx.edit(content="", embeds=[embed], components=[back_button, move_button])


@bot.command(name="profile", description="Lookup a player's rank/demons beaten/etc.",
             options=[interactions.Option(name="name", description="Player's name", type=interactions.OptionType.STRING, required=True)])
async def profile(ctx: interactions.CommandContext, name: str):
    # SELECT * FROM users
    # WHERE discord_id = {ctx.user.id};

    if not name:
        name = sql_query(sql_connection, f"SELECT * FROM users WHERE discord_id = {int(ctx.author.id)};") # this feature is unfinished
    out = await getProfile(ctx, name)
    if not out:
        return
    else:
        await ctx.send(embeds=out)


@bot.command(name="submitrecord", description="Submit a challenge record to the list",
             options=[interactions.Option(name="challenge", type=interactions.OptionType.STRING, required=True, description="Challenge name"),
                      interactions.Option(name="player", type=interactions.OptionType.STRING, required=True, description="Player"),
                      interactions.Option(name="video", type=interactions.OptionType.STRING, required=True, description="Progress video link"),
                      interactions.Option(name="raw_footage", type=interactions.OptionType.STRING, required=True, description="Raw footage link"),
                      interactions.Option(name="note", type=interactions.OptionType.STRING, required=False, description="Note")
                      ])
async def submitrecord(ctx: interactions.CommandContext, challenge, player, video, raw_footage, note):
    cChallenge = interactions.TextInput(
        style=interactions.TextStyleType.SHORT,
        label="Challenge",
        custom_id="mod_chess_input",
        min_length=1,
        max_length=6
    )

    try:
        # find ID
        cLevel = await correctLevel(challenge)
        demon_id = requests.get(f"https://challengelist.gd/api/v1/records/demons/?name_contains={challenge}", headers=headers).json()[0]["id"]

        r = requests.post("https://challengelist.gd/api/v1/records/",
                          json={"demon": demon_id, "player": player, "video": video,
                                "raw_footage": raw_footage,
                                "note": (note + f" (Requested with CLBot by {ctx.author.user.username}#{ctx.author.user.discriminator} / {int(ctx.author.user.id)})") if note
                                else f"Requested with CLBot by {ctx.author.user.username}#{ctx.author.user.discriminator} / {int(ctx.author.user.id)}",
                                "progress": 100}, headers=headers)

    except Exception as e:
        await ctx.send("**Error:** `" + str(e) + "`")
    else:
        if r.status_code == 200:
            await ctx.send(f"**Record sent successfully:** `{r.text}`")
        else:
            await ctx.send("**Couldn't send request, response code `" + str(r.status_code) + "`**")

@bot.command(name="getchallenge", description="Lookup completions of a challenge (make sure to use one of the two options)",
             options=[interactions.Option(name="level", description="Level name (not case-sensitive)", type=interactions.OptionType.STRING, required=False),
                      interactions.Option(name="position", description="List position", type=interactions.OptionType.INTEGER, required=False)])
async def getchallenge(ctx: interactions.CommandContext, level: str = None, position: int = None):
    g_level = None
    if not level and not position:
        await ctx.send("**Error:** No arguments provided!")
        return
    if level:
        out = await showChallenge(ctx, lvl_name=level, challenge_names=challenge_names_list)
        if type(out) == dict:
            out = out['autocorrect_resp']
            await ctx.send(embeds=out[0], components=out[1])
        elif not out:
            return
        else:
            pos = out[1]
            print(out)
            lastDemon = interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label="Back",
                custom_id="back_demon",
                disabled=False if (300 > pos > 1) else True
            )
            nextDemon = interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label="Next",
                custom_id="next_demon",
                disabled=False if (pos < 300) else True
            )
            await ctx.send(embeds=out[0], components=[lastDemon, nextDemon])
    else:
        out = await showChallenge(ctx, lvl_pos=position)
        lastDemon = interactions.Button(
            style=interactions.ButtonStyle.PRIMARY,
            label="Back",
            custom_id="back_demon",
            disabled=False if (250 > position > 1) else True
        )
        nextDemon = interactions.Button(
            style=interactions.ButtonStyle.PRIMARY,
            label="Next",
            custom_id="next_demon",
            disabled=False if (position < 250) else True
        )
        await ctx.send(embeds=out, components=[lastDemon, nextDemon])

@bot.component("levelcorrect")
async def levelcorrect(ctx: interactions.ComponentContext):
    lvl = ctx.component.label
    embed, position = await showChallenge(ctx, lvl_name=lvl)
    lastDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Back",
        custom_id="back_demon",
        disabled=False if (250 > position > 1) else True
    )
    nextDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next",
        custom_id="next_demon",
        disabled=False if (position < 250) else True
    )

    await ctx.send(embed=embed, components=[lastDemon, nextDemon])

@bot.component("next_demon")
async def nextchallenge(ctx: interactions.CommandContext):

    pos = int(ctx.message.embeds[0].title.split("#")[1].split(".")[0]) + 1
    embed = await showChallenge(ctx, lvl_pos=pos)

    lastDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Back",
        custom_id="back_demon",
        disabled=False if (250 > pos > 1) else True
    )
    nextDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next",
        custom_id="next_demon",
        disabled=False if (pos < 250) else True
    )
    await ctx.edit(content="", embeds=embed, components=[lastDemon, nextDemon])

@bot.component("back_demon")
async def backchallenge(ctx: interactions.CommandContext):

    pos = int(ctx.message.embeds[0].title.split("#")[1].split(".")[0]) - 1
    embed = await showChallenge(ctx, lvl_pos=pos)

    lastDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Back",
        custom_id="back_demon",
        disabled=False if (250 > pos > 1) else True
    )
    nextDemon = interactions.Button(
        style=interactions.ButtonStyle.PRIMARY,
        label="Next",
        custom_id="next_demon",
        disabled=False if (pos < 250) else True
    )
    await ctx.edit(content="", embeds=embed, components=[lastDemon, nextDemon])

bot.start()
