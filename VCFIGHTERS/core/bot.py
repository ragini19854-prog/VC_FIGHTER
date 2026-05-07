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
# plugins=dict(...) NAHI dalna — __main__.py ka load_handlers() handle karta hai
# Dono saath hote toh double registration hota tha
# ─────────────────────────────────────────────

app = Client(
    name="VCFIGHTER_BOT",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN,
    # plugins= REMOVED — double handler registration fix
)

log.info("⚙️ Bot client initialized")
