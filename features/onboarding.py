import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

PRONOUN_ROLES = ["she/her", "he/him", "they/them"]
PRONOUN_OPTIONS = PRONOUN_ROLES + ["prefer not to say"]
SUBTEAM_ROLES = ["Electrical", "Mechanical", "Firmware", "WebDev", "Management"]
WELCOME_CHANNEL = "welcome"
PICKER_MARKER = "electrium-onboarding-picker"

async def set_roles_from(member: discord.Member, managed: list[str], chosen: list[str]):
    guild = member.guild
    to_add = []
    to_remove = []
    for name in managed:
        role = discord.utils.get(guild.roles, name=name)
        if role is None:
            log.warning("Role %r does not exist in guild %s", name, guild.name)
            continue
        if name in chosen and role not in member.roles:
            to_add.append(role)
        elif name not in chosen and role in member.roles:
            to_remove.append(role)

    try:
        if to_add:
            await member.add_roles(*to_add)
        if to_remove:
            await member.remove_roles(*to_remove)
    except discord.Forbidden:
        log.warning(
            "Missing permission/hierarchy to change roles for %s. "
            "Bot needs Manage Roles and its role must sit above the target roles.",
            member,
        )

class PronounSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name) for name in PRONOUN_OPTIONS]
        super().__init__(
            placeholder="Select your pronouns...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="onboarding:pronouns",
        )

    async def callback(self, interaction: discord.Interaction):
        await set_roles_from(interaction.user, PRONOUN_ROLES, self.values)
        await interaction.response.send_message(
            f"Set your pronouns to **{self.values[0]}**.", ephemeral=True)


class SubteamSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name) for name in SUBTEAM_ROLES]
        super().__init__(
            placeholder="Select your subteam(s)...",
            min_values=0,
            max_values=len(SUBTEAM_ROLES),
            options=options,
            custom_id="onboarding:subteams",
        )

    async def callback(self, interaction: discord.Interaction):
        await set_roles_from(interaction.user, SUBTEAM_ROLES, self.values)
        chosen = ", ".join(self.values) if self.values else "none"
        await interaction.response.send_message(
            f"Updated your subteams to: **{chosen}**.", ephemeral=True
        )


class OnboardingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PronounSelect())
        self.add_item(SubteamSelect())


class Onboarding(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        self.bot.add_view(OnboardingView())

    def _build_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Welcome to Electrium!",
            description=(
                "Use the menus below to set your **pronouns** and **subteam(s)**.\n"
                "You can change these any time."
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=PICKER_MARKER)
        return embed

    async def _find_existing_picker(self, channel: discord.TextChannel):
        async for message in channel.history(limit=50):
            if message.author == self.bot.user and message.embeds:
                if message.embeds[0].footer.text == PICKER_MARKER:
                    return message
        return None

    @commands.Cog.listener()
    async def on_ready(self):
        for guild in self.bot.guilds:
            channel = discord.utils.get(guild.text_channels, name=WELCOME_CHANNEL)
            if channel is None:
                log.warning("No #%s channel in guild %s", WELCOME_CHANNEL, guild.name)
                continue
            if await self._find_existing_picker(channel):
                continue
            await channel.send(embed=self._build_embed(), view=OnboardingView())
            log.info("Posted onboarding picker in #%s (%s)", WELCOME_CHANNEL, guild.name)


async def setup(bot: commands.Bot):
    await bot.add_cog(Onboarding(bot))
