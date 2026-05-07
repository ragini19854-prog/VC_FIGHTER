# ╔══════════════════════════════════════════════════════════════╗
# ║         VCFIGHTER — Entry Point                              ║
# ║         File: VCFIGHTERS/__main__.py                         ║
# ╚══════════════════════════════════════════════════════════════╝

import asyncio
import importlib
import os

from pyrogram import idle

import Config
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.database.mangodb import (
    init_db,
    get_all_sessions,
    get_sudo_users,
)

log = LOGGER("VCFIGHTER")


# ─────────────────────────────────────────────
# CONFIG VALIDATION
# ─────────────────────────────────────────────

def validate_config():
    required = {
        "API_ID":    getattr(Config, "API_ID",    None),
        "API_HASH":  getattr(Config, "API_HASH",  None),
        "BOT_TOKEN": getattr(Config, "BOT_TOKEN", None),
        "MONGO_URI": getattr(Config, "MONGO_URI", None),
        "OWNER_ID":  getattr(Config, "OWNER_ID",  None),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        LOGGER("Config").error(
            f"❌ Missing config values: {missing}\n"
            "Please fill Config.py properly."
        )
        exit(1)
    LOGGER("Config").info("✅ Config validation passed")


# ─────────────────────────────────────────────
# MODULE AUTOLOADER  (FIGHTERS/ + Untils/)
# ─────────────────────────────────────────────

def _load_folder(package: str, folder_path: str):
    loaded, failed = [], []
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                importlib.import_module(f"VCFIGHTERS.{package}.{module_name}")
                loaded.append(module_name)
            except Exception as e:
                LOGGER("Loader").error(f"❌ Failed to load {package}/{module_name}: {e}")
                failed.append(module_name)
    return loaded, failed


def load_modules():
    base = os.path.dirname(__file__)

    # Load FIGHTERS/
    f_path = os.path.join(base, "FIGHTERS")
    f_loaded, f_failed = _load_folder("FIGHTERS", f_path)

    # Load Untils/  ← sudo.py lives here
    u_path = os.path.join(base, "Untils")
    u_loaded, u_failed = _load_folder("Untils", u_path)

    total_loaded = f_loaded + u_loaded
    total_failed = f_failed + u_failed

    LOGGER("Loader").info(
        f"✅ Loaded {len(total_loaded)} modules "
        f"({len(f_loaded)} FIGHTERS + {len(u_loaded)} Untils) | "
        f"❌ Failed: {len(total_failed)}"
    )
    if total_failed:
        LOGGER("Loader").warning(f"Failed: {total_failed}")


# ─────────────────────────────────────────────
# USERBOT LOADER
# ─────────────────────────────────────────────

async def load_userbots():
    from VCFIGHTERS.core.userbot import userbot_manager
    try:
        sessions = await get_all_sessions()
        if not sessions:
            LOGGER("Userbots").warning(
                "⚠️ No userbots in DB. Use /config → USERBOTs to add."
            )
            return
        await userbot_manager.start_all(sessions)
        LOGGER("Userbots").info(f"✅ {len(sessions)} userbot(s) started")
    except Exception as e:
        LOGGER("Userbots").error(f"❌ Userbot load failed: {e}")


# ─────────────────────────────────────────────
# MAIN INIT
# ─────────────────────────────────────────────

async def init():
    # ── 1. Config ──────────────────────────────
    validate_config()

    # ── 2. MongoDB ─────────────────────────────
    LOGGER("DB").info("🔌 Connecting to MongoDB...")
    await init_db()

    # ── 3. Bot app import (after DB is ready) ──
    from VCFIGHTERS.core.bot import app

    # ── 4. Load all modules ────────────────────
    LOGGER("Loader").info("📦 Loading modules...")
    load_modules()

    # ── 5. Start bot ───────────────────────────
    LOGGER("Bot").info("🤖 Starting bot...")
    await app.start()
    LOGGER("Bot").info("✅ Bot started")

    # ── 6. Start userbots ──────────────────────
    LOGGER("Userbots").info("👥 Starting userbots...")
    await load_userbots()

    # ── 7. Start PyTgCalls ─────────────────────
    LOGGER("PyTgCalls").info("📡 Starting PyTgCalls...")
    from VCFIGHTERS.core.call import vc
    await vc.start()
    LOGGER("PyTgCalls").info("✅ PyTgCalls ready")

    # ── 8. Banner ──────────────────────────────
    log.info(
        "\n╔══════════════════════════════════╗"
        "\n║  ⚔️  VCFIGHTER IS NOW ACTIVE  ⚔️  ║"
        "\n║     🔥 Ready to Destroy VCs 🔥    ║"
        "\n╚══════════════════════════════════╝"
    )

    # ── 9. Keep alive ──────────────────────────
    await idle()

    # ── 10. Graceful shutdown ──────────────────
    log.info("🛑 Shutting down...")
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.stop_all()
    except Exception: pass
    try:
        from VCFIGHTERS.core.call import vc
        await vc.stop()
    except Exception: pass
    await app.stop()
    log.info("✅ Shutdown complete")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(init())
        
