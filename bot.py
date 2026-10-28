"""Electrium Discord bot — entry point.

Boots the bot, initializes the database, registers slash commands, and provides
a `/ping` health check. Feature modules (onboarding, events, github) get added
on top of this foundation.

Run locally:
    python bot.py
(requires DISCORD_TOKEN in a .env file — see .env.example)
"""

from __future__ import annotations

import logging

import discord
from discord.ext import commands

import config
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("electrium-bot")

# Intents declare what the bot is allowed to receive.
# - members: required to react to joins and manage roles (onboarding).
# - message_content is deliberately NOT enabled — we use slash commands, so we
#   don't need to read message text.
intents = discord.Intents.default()
intents.members = True


class ElectriumBot(commands.Bot):
    def __init__(self) -> None:
        # command_prefix is unused (slash commands only) but required by the API.
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self) -> None:
        """Runs once before the bot connects. Set up DB, load features, sync commands."""
        db.init_db()
        logger.info("Database ready at %s", config.DB_PATH)

        # Feature modules. Add new cogs here as tracks land.
        for ext in ("cogs.onboarding", "cogs.events"):
            await self.load_extension(ext)
            logger.info("Loaded extension %s", ext)

        if config.GUILD_ID:
            guild = discord.Object(id=config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("Slash commands synced to guild %s", config.GUILD_ID)
        else:
            await self.tree.sync()
            logger.info("Slash commands synced globally (may take up to ~1h to appear)")


bot = ElectriumBot()


@bot.event
async def on_ready() -> None:
    if bot.user is None:
        return
    logger.info("Logged in as %s (id: %s)", bot.user, bot.user.id)
    logger.info("Serving %d guild(s)", len(bot.guilds))


@bot.tree.command(name="ping", description="Check that the bot is alive.")
async def ping(interaction: discord.Interaction) -> None:
    latency_ms = round(bot.latency * 1000)
    await interaction.response.send_message(
        f"Pong! 🟢 ({latency_ms} ms)", ephemeral=True
    )


def main() -> None:
    if not config.DISCORD_TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and fill it in."
        )
    # log_handler=None lets our logging.basicConfig above own the formatting.
    bot.run(config.DISCORD_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
