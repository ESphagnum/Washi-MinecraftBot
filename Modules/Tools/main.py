import discord
from discord.ext import commands
import requests, json

class Tools(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    async def color(color_id):
        color_name = color_id
        colors = {"green": 0x00ff00, "red": 0xff0000, "blue": 0x0000ff}
        return colors[color_name]

    async def respond(ctx, message: str=None, color=0x000000, embed: discord.Embed=None, view: discord.ui.View=None):
        if embed is not None and message is not None:
            raise AttributeError("Message is not None when embed is also not None")
        if embed is None:
            embed = discord.Embed(title=message, color=color)
        try:
            return await ctx.reply(embed=embed, mention_author=False, view=view)
        except:
            return await ctx.respond(embed=embed, view=view)
    
    async def webhook(ctx, url, file):
        data = json.load(file)

        headers={"Content-Type": "application/json"}
        requests.post(url, data=json.dumps(data), headers=headers)


    @commands.command(name='webhook')
    async def webhook(self, ctx, *args):
        # if not args.isdigit():
        #     await Tools.respond(ctx, embed=discord.Embed(title="Webhook").add_field(name="**Commands**", value="**\n!webhook create <id> <avatar_url>\n!webhook delete <id>\n!webhook list\n!webhook message <SendWithFile.json (Guide)[https://birdie0.github.io/discord-webhooks-guide/structure/username.html]>**"))
        if len(ctx.message.attachments) == 0:
            return await Tools.respond(ctx, "Прикрепите файл", color=0xff0000)
        attachment = ctx.message.attachments[0]
        Tools.webhook(ctx, args[0], attachment)
        




async def setup(bot):
    cog = Tools(bot)
    await bot.add_cog(cog)