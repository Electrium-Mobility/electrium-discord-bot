"""Configuration loaded from environment / .env.

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

import json

RUNTIME_CONFIG_PATH: str = os.getenv("RUNTIME_CONFIG_PATH", "runtime_config.json")

_DEFAULT_RUNTIME_CONFIG = {
    "reminder_window_minutes": 60,
    "general_resources": [],
}


def load_runtime_config() -> dict:
    path = os.path.abspath(RUNTIME_CONFIG_PATH)
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump(_DEFAULT_RUNTIME_CONFIG, f, indent=2)
        return dict(_DEFAULT_RUNTIME_CONFIG)
    with open(path) as f:
        return json.load(f)


def save_runtime_config(data: dict) -> None:
    path = os.path.abspath(RUNTIME_CONFIG_PATH)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)