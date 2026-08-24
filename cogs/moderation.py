import logging

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger("electrium-bot")


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="delete", description="Delete recent messages")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def delete(self, interaction: discord.Interaction, amount: int):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("pick a number 1-100", ephemeral=True)
            return

        if not isinstance(interaction.channel, discord.TextChannel):
            await interaction.response.send_message("can't do that here", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        deleted = await interaction.channel.purge(limit=amount)
        logger.info("%s deleted %d messages in #%s", interaction.user, len(deleted), interaction.channel)
        await interaction.followup.send(f"deleted {len(deleted)} messages", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))