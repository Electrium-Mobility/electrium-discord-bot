"""Web dashboard for editing bot config without touching code.

Covers reminder_window_minutes and general_resources
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse

import config

logger = logging.getLogger("electrium-bot.web")

app = FastAPI(title="Electrium Bot Config")


def _render(cfg: dict, saved: bool = False) -> str:
    resources = cfg["general_resources"] or [{"label": "", "url": ""}]
    resources_rows = "".join(
        f"""
        <tr>
            <td><input name="resource_label" value="{r['label']}" placeholder="Label"></td>
            <td><input name="resource_url" value="{r['url']}" placeholder="https://..."></td>
        </tr>
        """
        for r in resources
    )
    banner = "<p style='color:green'>Saved ✅</p>" if saved else ""
    return f"""
    <html>
    <head><title>Electrium Bot Config</title></head>
    <body style="font-family: sans-serif; max-width: 600px; margin: 40px auto;">
        <h1>Electrium Bot Config</h1>
        {banner}
        <form method="post" action="/save">
            <label>Reminder window (minutes)</label><br>
            <input name="reminder_window_minutes" value="{cfg['reminder_window_minutes']}"><br><br>
            <h3>General Resources</h3>
            <table>{resources_rows}</table>
            <br>
            <button type="submit">Save</button>
        </form>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    cfg = config.load_runtime_config()
    return _render(cfg)


@app.post("/save", response_class=HTMLResponse)
async def save(
    reminder_window_minutes: int = Form(...),
    resource_label: list[str] = Form(default=[]),
    resource_url: list[str] = Form(default=[]),
) -> str:
    cfg = {
        "reminder_window_minutes": reminder_window_minutes,
        "general_resources": [
            {"label": label, "url": url}
            for label, url in zip(resource_label, resource_url)
        ],
    }
    config.save_runtime_config(cfg)
    logger.info("Runtime config updated via dashboard")
    return _render(cfg, saved=True)