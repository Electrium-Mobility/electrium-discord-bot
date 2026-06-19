# Electrium Discord Bot

Discord bot for the Electrium Mobility team.

## Prerequisites

- **Python 3.12** — <https://www.python.org/downloads/> (on Windows, tick **"Add python.exe to PATH"** during install)
- **Git**

## 1. Create your bot

> Each contributor should use **their own** bot and **their own** test server, so you don't collide while developing.

1. Go to <https://discord.com/developers/applications> → **New Application**.
2. **Bot** → **Reset Token** → copy the token (keep it secret — it goes in `.env`).
3. **Bot** → enable **Server Members Intent** → **Save Changes**.
4. **OAuth2 → URL Generator** → scopes **`bot`** + **`applications.commands`**; bot permissions **Manage Roles**, **Send Messages**, **View Channels**. Open the generated URL and add the bot to your test server.

## 2. Install

```bash
git clone https://github.com/Electrium-Mobility/electrium-discord-bot.git
cd electrium-discord-bot
python -m venv .venv

# activate the venv:
.\.venv\Scripts\activate      # Windows (PowerShell)
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

## 3. Configure

Copy `.env.example` to `.env` and fill in:

- `DISCORD_TOKEN` — your bot token from step 1
- `GUILD_ID` — your test server's ID (enable **Developer Mode** in Discord → right-click the server icon → **Copy Server ID**)

## 4. Run

```bash
python bot.py
```

Type `/ping` in your test server — the bot replies **Pong**.

---

Opening the folder in **VS Code**? It's preconfigured to use `.venv` (via `.vscode/settings.json`). If imports show as unresolved, run **Ctrl+Shift+P → Python: Select Interpreter** and pick the `.venv` one.
