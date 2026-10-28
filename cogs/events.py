"""Events: /event create posts an event that members can RSVP to."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

import db

logger = logging.getLogger("electrium-bot.events")

#since the design team is in Waterloo, so times people type are Toronto time.
LOCAL_TZ = ZoneInfo("America/Toronto")
TIME_FORMAT = "%Y-%m-%d %H:%M"  # e.g. 2026-10-30 18:00

def parse_when(text: str) -> datetime:
    """Turn '2026-10-30' (Toronto time) into a UTC datetime.
    
    Raises ValueError with a friendly message if the text is wrong or in the past.
    """
    try:
        naive = datetime.strptime(text.strip(), TIME_FORMAT)
    except ValueError:
        raise ValueError("Use the format `YYYY-MM-DD HH:MM`, e.g. `2026-10-30 18:00`.")
    local = naive.replace(tzinfo=LOCAL_TZ)
    utc = local.astimezone(timezone.utc)
    if utc <= datetime.now(timezone.utc):
        raise ValueError("That time is in the past.")
    return utc

class Events(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    event = app_commands.Group(name="event", description="Team events")

    @event.command(name="create", description="create an event members can RSVP to.")
    @app_commands.describe(
        title="what is it? e.g. Bike team meeting",
        when="Toronto time, format YYYY-MM-DD HH:MM",
        location="Where? (optional)",
    )
    async def create(
        self,
        interaction: discord.Interaction,
        title: str,
        when: str,
        location: str | None = None,
    ) -> None:
        try:
            starts_at = parse_when(when)
        except ValueError as e:
            await interaction.response.send_message(f"⚠️ {e}", ephemeral=True)
            return

        now = datetime.now(timezone.utc).isoformat()
        event_id = db.add_event(title, starts_at.isoformat(), location, interaction.user.id, now)

        unix = int(starts_at.timestamp())
        await interaction.response.send_message(
            f"✅ Created event **#{event_id}: {title}** on <t:{unix}:F> (<t:{unix}:R>)"
        )

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))