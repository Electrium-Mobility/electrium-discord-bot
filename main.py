import discord
from discord.ext import commands
from dotenv import load_dotenv
from aiohttp import web
import os

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
guild_id = os.getenv("GUILD_ID")  # optional: instant slash-command sync to one server

intents = discord.Intents.default()
intents.message_content = True


# Web server + UptimeRobot pings the url
async def start_keepalive_server():
    app = web.Application()
    app.router.add_get("/", lambda request: web.Response(text="ok"))
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    await web.TCPSite(runner, host="0.0.0.0", port=port).start()


class ElectriumBot(commands.Bot):
    # setup_hook runs once before the bot connects.
    async def setup_hook(self):
        await start_keepalive_server()
        #load extensions
        await self.load_extension("features.onboarding")
        await self.load_extension("features.events")
        # Register slash commands with Discord
        if guild_id:
            guild = discord.Object(id=int(guild_id))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()


bot = ElectriumBot(command_prefix = '!', intents = intents)

bot.run(token)
