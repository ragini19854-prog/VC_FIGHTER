# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — Main Bot Client                          ║
# ║         File: VCFIGHTERS/core/bot.py                         ║
# ╚══════════════════════════════════════════════════════════════╝

from pyrogram import Client

import Config
from VCFIGHTERS.logging import LOGGER

log = LOGGER("Bot")

# ─────────────────────────────────────────────
# MAIN BOT CLIENT — Singleton
# ─────────────────────────────────────────────

app = Client(
    name="VCFIGHTER_BOT",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    plugins=dict(root="VCFIGHTERS"),  # handlers auto-register
)

log.info("⚙️ Bot client initialized")
