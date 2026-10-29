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
RSVP_OPTIONS = [
    ("going", "Going", "✅"),
    ("maybe", "Maybe", "🤔"),
    ("cant", "Can't", "❌"),
]

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

def build_event_embed(event, counts: dict[str, int]) -> discord.Embed:
    """Draw the event card from a database row and the RSVP counts"""
    starts_at = datetime.fromisoformat(event["starts_at"])
    unix = int(starts_at.timestamp())

    embed = discord.Embed(
        title=f"📅 {event['title']}",
        description=f"Hosted by <@{event['created_by']}>",
        color=discord.Color.blurple(),
    )
    embed.add_field(name="When", value=f"<t:{unix}:F>\n<t:{unix}:R>", inline=False)
    if event["location"]:
        embed.add_field(name="Where", value=event["location"], inline=False)
    for key, label, emoji in RSVP_OPTIONS:
        embed.add_field(name=f"{emoji} {label}", value=str(counts.get(key, 0)),inline=True)
    embed.set_footer(text=f"Event #{event['id']}")
    return embed

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

        event = db.get_event(event_id)
        assert event is not None # we just insert it, so it must exist
        embed = build_event_embed(event, db.get_rsvp_counts(event_id))

        await interaction.response.send_message(embed=embed)

        #remember which message is this event's card, so later steps can edit it.
        message = await interaction.original_response()
        db.attach_message(event_id, message.channel.id, message.id)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Events(bot))