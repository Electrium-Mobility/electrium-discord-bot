"""Onboarding + role buttons (Track A: A2 + A3 + A4).

Flow:
  * An admin runs /post-onboarding in a channel (e.g. #welcome). The bot posts a
    persistent message with one button per sub-team. (A2)
  * A member clicks a button -> the matching role is toggled on/off, and their
    sub-team channels unlock. Clicking again leaves the team. (A3)
  * When a member JOINS a team, the bot DMs them getting-started links. (A4)

The buttons are a *persistent* view (timeout=None + stable custom_ids + add_view
in setup), so they keep working even after the bot restarts.

Design note: buttons are toggles, so a member can be on multiple sub-teams (click
to join, click again to leave). If the team prefers "exactly one sub-team", say so
and we'll switch to single-select (clicking one removes the others).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

import db

logger = logging.getLogger("electrium-bot.onboarding")


# The sub-teams. `label` must match the Discord role name (case-insensitive).
SUBTEAMS = [
    {"key": "mechanical", "label": "Mechanical", "emoji": "⚙️"},   # ⚙️
    {"key": "electrical", "label": "Electrical", "emoji": "⚡"},          # ⚡
    {"key": "firmware",   "label": "Firmware",   "emoji": "\U0001f527"},      # 🔧
    {"key": "webdev",     "label": "WebDev",     "emoji": "\U0001f310"},      # 🌐
    {"key": "management",  "label": "Management", "emoji": "\U0001f4cb"},     # 📋
]

# Getting-started links DM'd when a member joins a team (A4).
# TODO(team): replace these placeholder URLs with the real onboarding hub / docs.
GENERAL_RESOURCES = [
    ("Onboarding hub", "https://example.com/electrium/onboarding"),
    ("Safety docs", "https://example.com/electrium/safety"),
]
SUBTEAM_RESOURCES: dict[str, list[tuple[str, str]]] = {
    "mechanical": [("Mechanical getting-started", "https://example.com/electrium/mechanical")],
    "electrical": [("Electrical getting-started", "https://example.com/electrium/electrical")],
    "firmware":   [("Firmware getting-started", "https://example.com/electrium/firmware")],
    "webdev":     [("WebDev getting-started", "https://example.com/electrium/webdev")],
    "management": [("Management getting-started", "https://example.com/electrium/management")],
}


def _find_role(guild: discord.Guild, label: str) -> discord.Role | None:
    """Find a role by name, case-insensitively (forgiving of capitalization)."""
    return discord.utils.find(lambda r: r.name.lower() == label.lower(), guild.roles)


async def _send_resources_dm(member: discord.Member, subteam: dict) -> None:
    """DM the new team member their getting-started links. Silent if DMs are closed."""
    links = GENERAL_RESOURCES + SUBTEAM_RESOURCES.get(subteam["key"], [])
    body = [f"Welcome to **Electrium Mobility**! You joined **{subteam['label']}**.", ""]
    body += [f"• [{label}]({url})" for label, url in links]
    embed = discord.Embed(description="\n".join(body), color=discord.Color.green())
    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        # Member has DMs disabled — the ephemeral confirmation already covered it.
        logger.info("Could not DM resources to %s (DMs closed).", member)


async def _handle_click(interaction: discord.Interaction, subteam: dict) -> None:
    """Toggle the sub-team role for the clicking member, with clear error messages."""
    guild = interaction.guild
    member = interaction.user  # a Member in guild-component context
    if guild is None or not isinstance(member, discord.Member):
        await interaction.response.send_message("This only works inside the server.", ephemeral=True)
        return

    role = _find_role(guild, subteam["label"])
    if role is None:
        await interaction.response.send_message(
            f"⚠️ The **{subteam['label']}** role doesn't exist yet. "
            "An admin needs to create a role with that name.",
            ephemeral=True,
        )
        return

    # The bot can only manage roles below its own highest role.
    if role >= guild.me.top_role:
        await interaction.response.send_message(
            f"⚠️ I can't assign **{subteam['label']}** — my role sits below it. "
            "An admin needs to drag my role above the sub-team roles.",
            ephemeral=True,
        )
        return

    try:
        if role in member.roles:
            await member.remove_roles(role, reason="Onboarding: left sub-team")
            await interaction.response.send_message(
                f"➖ Removed you from **{subteam['label']}**.", ephemeral=True
            )
        else:
            await member.add_roles(role, reason="Onboarding: joined sub-team")
            db.set_sub_team(member.id, subteam["key"], datetime.now(timezone.utc).isoformat())
            await interaction.response.send_message(
                f"✅ You're now in **{subteam['label']}**! Your new channels just unlocked.",
                ephemeral=True,
            )
            await _send_resources_dm(member, subteam)
    except discord.Forbidden:
        await interaction.response.send_message(
            "⚠️ I don't have the **Manage Roles** permission. An admin needs to grant it.",
            ephemeral=True,
        )


class SubteamButton(discord.ui.Button):
    """One button per sub-team. Stable custom_id makes the view persistent."""

    def __init__(self, subteam: dict) -> None:
        super().__init__(
            label=subteam["label"],
            emoji=subteam["emoji"],
            style=discord.ButtonStyle.secondary,
            custom_id=f"onboard:{subteam['key']}",
        )
        self.subteam = subteam

    async def callback(self, interaction: discord.Interaction) -> None:
        await _handle_click(interaction, self.subteam)


class OnboardingView(discord.ui.View):
    """Persistent view holding all the sub-team buttons."""

    def __init__(self) -> None:
        super().__init__(timeout=None)
        for subteam in SUBTEAMS:
            self.add_item(SubteamButton(subteam))


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="post-onboarding",
        description="Post the sub-team role picker in this channel.",
    )
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.checks.has_permissions(manage_roles=True)
    async def post_onboarding(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="Join a sub-team \U0001f6f9⚡",
            description=(
                "Click a button to **join** that sub-team — your channels unlock "
                "automatically. Click it again to leave. You can be on more than one."
            ),
            color=discord.Color.green(),
        )
        await interaction.channel.send(embed=embed, view=OnboardingView())
        await interaction.response.send_message("Posted the role picker ✅", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        db.upsert_member(member.id, datetime.now(timezone.utc).isoformat())
        try:
            await member.send(
                "Welcome to **Electrium Mobility**! \U0001f44b\n"
                "Head to the server and pick your sub-team(s) in the welcome channel "
                "to unlock your team's channels."
            )
        except discord.Forbidden:
            logger.info("Could not DM welcome to %s (DMs closed).", member)

    async def cog_app_command_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            msg = "You need the **Manage Roles** permission to use that command."
        else:
            msg = "Something went wrong handling that command."
            logger.exception("Unhandled app command error", exc_info=error)
        if interaction.response.is_done():
            await interaction.followup.send(msg, ephemeral=True)
        else:
            await interaction.response.send_message(msg, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Onboarding(bot))
    # Register the persistent view so buttons keep working across restarts.
    bot.add_view(OnboardingView())
