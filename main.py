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


token = load(open("token.json"))['token']

agent = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
headers = {"User-Agent": agent}

sql_creds = load(open("sql_creds.json"))
bot = interactions.Client(token=token)

sql_connection = create_connection(sql_creds['host'], sql_creds['database'], sql_creds['username'], sql_creds['password'])

challenge_names_list = ()
async def updateLevels():
    global challenge_names_list
    levels_list = []
    i = 0
    while i <= 250:
        r = to_json(requests.get(f"https://challengelist.gd/api/v1/demons/?limit=50&after={i}", headers=headers).text)
        #print(r)
        for level in r:
            levels_list.append(level['name'].lower())
            #print(level['name'])
        i += 50
    challenge_names_list = tuple(levels_list)

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
        await ctx.send(embeds=out[0], components=[out[1], out[2]])
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
    embed = await getChallenges(limit, None if not page else page * limit, title)
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
    p = to_json(requests.get(f"https://challengelist.gd/api/v1/players/ranking/?name_contains={name}", headers=headers).text)
    if not p:
        if "@everyone" in name.lower() or "@here" in name.lower():
            # await ctx.author.kick(ctx.guild_id) # come on man... really?
            await ctx.send("Couldn't find any player with that name, try again (a typo maybe?)")
            pass
        else:
            await ctx.send("Couldn't find any player with that name, try again (a typo maybe?)")
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
        more_details = to_json(requests.get(f"https://challengelist.gd/api/v1/players/{id}", headers=headers).text)['data']
        created_demons = []
        for demon in more_details['created']:
            created_demons.append(f"**{demon['name']}** (#{demon['position']})")
        created_demons = ', '.join(created_demons) if created_demons else "None"

        published_demons = []
        for demon in more_details['published']:
            published_demons.append(f"**{demon['name']}** (#{demon['position']})")
        published_demons = ', '.join(published_demons) if published_demons else "None"

        completed_demons, progress_demons, legacy_demons = [], [], []
        for record in more_details['records']:
            if record['progress'] < 100:
                progress_demons.append(f"**{record['demon']['name']}** {record['progress']}%")
            elif record['demon']['position'] > 100:
                if "❌" in record['demon']['name']:
                    legacy_demons.append(f"*{record['demon']['name']}*")
                else:
                    legacy_demons.append(f"{record['demon']['name']}")
            else:
                completed_demons.append(f"{record['demon']['name']}")

        completed_demons = ', '.join(completed_demons) if completed_demons else "None"
        legacy_demons = ', '.join(legacy_demons) if legacy_demons else "None"
        progress_demons = ', '.join(progress_demons) if progress_demons else "None"
        cCountry = f":flag_{p['nationality']['country_code'].lower()}:" if p['nationality'] else ":question:"
        embed = interactions.Embed(color=0xffae00, title=f"{p['name']} {cCountry}")
        embed.add_field(name="Overview",
                        value=f"**Rank:** #{rank} {badge}\n **{round(p['score'], 2)}** points\n**Nationality:** {p['nationality']['nation'] if p['nationality'] else 'Unknown'}")
        embed.add_field(name="Challenges created", value=published_demons)
        embed.add_field(name="Verified challenges", value=created_demons)
        embed.add_field(name="Completed challenges", value=(completed_demons[:1021] + "...") if len(completed_demons) > 1020 else completed_demons)
        embed.add_field(name="Completed challenges (legacy)", value=(legacy_demons[:1021] + "...") if len(legacy_demons) > 1020 else legacy_demons)

        await ctx.send(embeds=embed)


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
                disabled=False if (250 > pos > 1) else True
            )
            nextDemon = interactions.Button(
                style=interactions.ButtonStyle.PRIMARY,
                label="Next",
                custom_id="next_demon",
                disabled=False if (pos < 250) else True
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
