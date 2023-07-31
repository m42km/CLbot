from interactions import Embed, User, EmbedFooter

async def errorEmbed(e: Exception) -> Embed:
    details = "Sorry, an error occurred: \n" + str(e)[:90] + "..."
    embed = Embed(title="Error", description=f"```py\n{details}```", color=0xFF7777)
    return embed

async def successEmbed(desc: str) -> Embed:
    return Embed(title="Success", description=desc, color=0x66FF66)

