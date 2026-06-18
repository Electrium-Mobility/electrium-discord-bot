# Electrium Discord Bot

Automates the team's weekly manual work in Discord. MVP features:

1. **Onboarding + role buttons** — new members self-assign a sub-team; roles unlock channels.
2. **Meeting reminders + RSVP** — schedule events, members RSVP, bot pings before.
3. **GitHub channel** — repo activity posts to `#dev`.

See [`docs/DISCORD-BOT-TASKS.md`](../Outreach-tool-main/docs/DISCORD-BOT-TASKS.md) for the full task board.

## Foundation status

| Task | What | Status |
|---|---|---|
| F1 | Bot scaffold + `/ping` | ✅ code done — needs your token to run |
| F2 | Hosting / deploy | ⏳ `Procfile` ready — pick a host |
| F3 | SQLite persistence layer | ✅ `db.py` |

## Project layout

```
electrium-discord-bot/
├── bot.py            # entry point: boots bot, syncs commands, /ping  (F1)
├── config.py         # loads settings from .env                        (F1)
├── db.py             # SQLite schema + helpers for all features        (F3)
├── requirements.txt
├── .env.example      # copy to .env and fill in
├── Procfile          # for Railway / Fly.io / Heroku-style hosts        (F2)
└── .gitignore
```

## Run it locally

### 1. Create the bot in Discord (one-time, ~5 min)
1. Go to <https://discord.com/developers/applications> → **New Application**, name it "Electrium Bot".
2. Left sidebar → **Bot** → **Reset Token** → copy the token (you'll paste it into `.env`).
3. On the same Bot page, scroll to **Privileged Gateway Intents** and enable **Server Members Intent** (Track A onboarding needs it). Save.
4. Left sidebar → **OAuth2** → **URL Generator**: tick **`bot`** and **`applications.commands`** scopes; under Bot Permissions tick **Manage Roles**, **Send Messages**, **Read Messages/View Channels**. Copy the generated URL, open it, and invite the bot to your **test server**.

### 2. Set up the project
```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env       # then edit .env: paste DISCORD_TOKEN and your test GUILD_ID
```

### 3. Run
```powershell
python bot.py
```
In your test server, type `/ping` — the bot should reply "Pong! 🟢". That's F1 + F3 working.

## Deploy (F2)

The `Procfile` runs the bot as a **worker** (not a web service — it makes an outbound
connection to Discord, it doesn't serve HTTP). Recommended free/cheap options:

- **Railway** or **Fly.io** — connect this repo, set `DISCORD_TOKEN` (and optionally
  `GUILD_ID`) as environment variables in the host's dashboard, deploy.
- **Raspberry Pi in the lab** — `pip install -r requirements.txt` and run under
  `systemd` or `pm2` so it restarts on reboot.

Whichever you pick: **the token goes in the host's secret/env settings, never in git.**
