import json
import logging
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

EVENTS_FILE = Path(__file__).resolve().parent.parent / "events.json"
TEAM_TZ = ZoneInfo("America/Toronto")
DATE_FORMAT = "%Y-%m-%d %H:%M"  # e.g. 2026-06-27 18:00

# JSON storage helper
def load_events() -> dict:
    if not EVENTS_FILE.exists():
        return {}
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

# JSON storage helper
def save_events(events: dict):
    with open(EVENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)


# Build the embed shown for an event
def build_event_embed(guild: discord.Guild, data: dict) -> discord.Embed:
    embed = discord.Embed(
        title=data["title"],
        description=f"**When:** <t:{data['ts']}:F> (<t:{data['ts']}:R>)",
        color=discord.Color.green(),
    )
    if data.get("link"):
        embed.add_field(name="Join link", value=data["link"], inline=False)

    embed.add_field(name="​", value=_format_names(guild, "Going", data["going"]), inline=False)
    embed.add_field(name="​", value=_format_names(guild, "Not Going", data["not_going"]), inline=False)
    return embed


def _format_names(guild: discord.Guild, label: str, user_ids: list) -> str:
    if not user_ids:
        return f"**{label} (0)**\n—"
    names = []
    for uid in user_ids:
        member = guild.get_member(uid)
        names.append(member.display_name if member else f"<@{uid}>")
    return f"**{label} ({len(user_ids)})**\n" + ", ".join(names)


class RSVPButton(discord.ui.Button):
    def __init__(self, message_id: str, going: bool):
        self.going = going
        super().__init__(
            label="Going" if going else "Not Going",
            style=discord.ButtonStyle.success if going else discord.ButtonStyle.danger,
            custom_id=f"event:{'going' if going else 'notgoing'}:{message_id}",
        )

    async def callback(self, interaction: discord.Interaction):
        message_id = str(interaction.message.id)
        events = load_events()
        data = events.get(message_id)
        if data is None:
            await interaction.response.send_message(
                "This event no longer exists.", ephemeral=True)
            return

        uid = interaction.user.id
        chosen, other = ("going", "not_going") if self.going else ("not_going", "going")
        if uid not in data[chosen]:
            data[chosen].append(uid)
        if uid in data[other]:
            data[other].remove(uid)

        save_events(events)

        embed = build_event_embed(interaction.guild, data)
        await interaction.response.edit_message(embed=embed)


class EventView(discord.ui.View):
    def __init__(self, message_id: str):
        super().__init__(timeout=None)
        self.add_item(RSVPButton(message_id, going=True))
        self.add_item(RSVPButton(message_id, going=False))


# Save the event and post its embed + RSVP buttons.
async def post_event(channel: discord.abc.Messageable, guild: discord.Guild, data: dict):
    embed = build_event_embed(guild, data)
    message = await channel.send(embed=embed)
    await message.edit(view=EventView(str(message.id)))

    events = load_events()
    events[str(message.id)] = data
    save_events(events)
    log.info("Created event %r (%s)", data["title"], message.id)


# The pop-up form opened by /event create.
class EventModal(discord.ui.Modal, title="Create Event"):
    event_title = discord.ui.TextInput(label="Title", placeholder="Team Meeting")
    date = discord.ui.TextInput(label="Date", placeholder="2026-06-27")
    time = discord.ui.TextInput(label="Time (24-hour)", placeholder="18:00")
    link = discord.ui.TextInput(
        label="Link (optional)", required=False, placeholder="https://meet.google.com/..."
    )

    async def on_submit(self, interaction: discord.Interaction):
        ts = _parse_datetime(f"{self.date.value.strip()} {self.time.value.strip()}")
        if ts is None:
            await interaction.response.send_message(
                "Couldn't read that date/time. Use Date `YYYY-MM-DD` and Time `HH:MM`.",
                ephemeral=True,
            )
            return

        data = {
            "title": self.event_title.value.strip(),
            "ts": ts,
            "link": self.link.value.strip() or None,
            "channel_id": interaction.channel.id,
            "going": [],
            "not_going": [],
        }
        await post_event(interaction.channel, interaction.guild, data)
        await interaction.response.send_message("Event posted.", ephemeral=True)


# /event <subcommand> as a slash-command group.
class EventGroup(app_commands.Group):
    def __init__(self, bot: commands.Bot):
        super().__init__(name="event", description="Create and manage events")
        self.bot = bot

    @app_commands.command(name="create", description="Create an event (opens a form)")
    @app_commands.checks.has_permissions(manage_events=True)
    async def create(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EventModal())

    @app_commands.command(name="list", description="Show all events")
    async def list(self, interaction: discord.Interaction):
        events = load_events()
        lines = []
        for message_id, data in events.items():
            try:
                link = f" — {data['link']}" if data.get("link") else ""
                lines.append(
                    f"**{data['title']}** (<t:{data['ts']}:F>){link}\n"
                    f"   {len(data['going'])} going · {len(data['not_going'])} not going"
                )
            except (KeyError, TypeError):
                log.warning("Skipping malformed event entry %s in list", message_id)

        await interaction.response.send_message(
            "\n".join(lines) if lines else "No events yet.", ephemeral=True
        )

    @app_commands.command(name="delete", description="Delete an event by title or message id")
    @app_commands.describe(target="Event title (exact) or its message id")
    @app_commands.checks.has_permissions(manage_events=True)
    async def delete(self, interaction: discord.Interaction, target: str):
        events = load_events()

        if target.isdigit():
            matches = [target] if target in events else []
        else:
            matches = [mid for mid, d in events.items() if d["title"] == target]

        if not matches:
            await interaction.response.send_message("No event found matching that.", ephemeral=True)
            return
        if len(matches) > 1:
            ids = ", ".join(f"`{m}`" for m in matches)
            await interaction.response.send_message(
                f"Multiple events share that title. Delete by id instead: {ids}",
                ephemeral=True,
            )
            return

        message_id = matches[0]
        data = events.pop(message_id)
        save_events(events)

        channel = self.bot.get_channel(data["channel_id"])
        if channel is not None:
            try:
                message = await channel.fetch_message(int(message_id))
                await message.delete()
            except discord.NotFound:
                pass
            except discord.Forbidden:
                log.warning("Missing permission to delete event message %s", message_id)

        await interaction.response.send_message(
            f"Deleted event **{data['title']}**.", ephemeral=True
        )
        log.info("Deleted event %r (%s)", data["title"], message_id)


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.tree.add_command(EventGroup(bot))

    # Re-register a view per saved event so old buttons keep working after restart.
    async def cog_load(self):
        events = load_events()
        for message_id in events:
            self.bot.add_view(EventView(message_id))


# Parse "YYYY-MM-DD HH:MM" (team timezone) into a Unix timestamp, or None.
def _parse_datetime(text: str):
    try:
        dt = datetime.strptime(text.strip(), DATE_FORMAT).replace(tzinfo=TEAM_TZ)
    except ValueError:
        return None
    return int(dt.timestamp())


async def setup(bot: commands.Bot):
    await bot.add_cog(Events(bot))
