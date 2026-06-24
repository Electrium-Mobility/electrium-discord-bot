import discord
from discord.ext import commands
from dotenv import load_dotenv
import os

load_dotenv()
token = os.getenv("DISCORD_TOKEN")
guild_id = os.getenv("GUILD_ID")  # optional: instant slash-command sync to one server

intents = discord.Intents.default()
intents.message_content = True


class ElectriumBot(commands.Bot):
    # setup_hook runs once before the bot connects.
    async def setup_hook(self):
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
