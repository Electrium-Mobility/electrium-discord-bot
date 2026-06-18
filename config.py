"""Configuration loaded from environment / .env (Task F1).

Keeping this in one place means every other module imports settings from here
rather than reading os.environ scattered around the codebase.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()

# Required: the bot's login token.
DISCORD_TOKEN: str | None = os.getenv("DISCORD_TOKEN")

# Optional: a single guild (server) ID. When set, slash commands sync to that
# server instantly — ideal for development. When unset, commands sync globally.
_guild_raw = os.getenv("GUILD_ID", "").strip()
GUILD_ID: int | None = int(_guild_raw) if _guild_raw.isdigit() else None

# Where the SQLite file lives.
DB_PATH: str = os.getenv("DB_PATH", "electrium_bot.db")
