import asyncio

try:
    asyncio.set_event_loop(asyncio.new_event_loop())
except Exception:
    pass

import importlib
import os
from pyrogram import idle
import Config
from VCFIGHTERS.logging import LOGGER
from VCFIGHTERS.database.mangodb import init_db, get_all_sessions

log = LOGGER("VCFIGHTER")

def validate_config():
    required = {
        "API_ID": getattr(Config, "API_ID", None),
        "API_HASH": getattr(Config, "API_HASH", None),
        "BOT_TOKEN": getattr(Config, "BOT_TOKEN", None),
        "MONGO_URI": getattr(Config, "MONGO_URI", None),
        "OWNER_ID": getattr(Config, "OWNER_ID", None),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        LOGGER("Config").error(f"Missing config values: {missing}")
        exit(1)
    LOGGER("Config").info("Config validation passed")

def _load_folder(package: str, folder_path: str):
    loaded, failed = [], []
    for filename in sorted(os.listdir(folder_path)):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            try:
                importlib.import_module(f"VCFIGHTERS.{package}.{module_name}")
                loaded.append(module_name)
            except Exception as e:
                LOGGER("Loader").error(f"Failed to load {package}/{module_name}: {e}")
                failed.append(module_name)
    return loaded, failed

def load_modules():
    base = os.path.dirname(__file__)
    f_path = os.path.join(base, "FIGHTERS")
    f_loaded, f_failed = _load_folder("FIGHTERS", f_path)
    u_path = os.path.join(base, "Untils")
    u_loaded, u_failed = _load_folder("Untils", u_path)
    
    total_loaded = f_loaded + u_loaded
    total_failed = f_failed + u_failed
    
    LOGGER("Loader").info(f"Loaded {len(total_loaded)} modules | Failed: {len(total_failed)}")

async def load_userbots():
    from VCFIGHTERS.core.userbot import userbot_manager
    try:
        sessions = await get_all_sessions()
        if not sessions:
            LOGGER("Userbots").warning("No userbots in DB.")
            return
        await userbot_manager.start_all(sessions)
        LOGGER("Userbots").info(f"{len(sessions)} userbot(s) started")
    except Exception as e:
        LOGGER("Userbots").error(f"Userbot load failed: {e}")

async def init():
    validate_config()
    LOGGER("DB").info("Connecting to MongoDB...")
    await init_db()
    
    from VCFIGHTERS.core.bot import app
    
    LOGGER("Loader").info("Loading modules...")
    load_modules()
    
    LOGGER("Bot").info("Starting bot...")
    await app.start()
    LOGGER("Bot").info("Bot started")
    
    for group, handlers in app.dispatcher.groups.items():
        log.info(f"[DEBUG] Group {group} mein {len(handlers)} handlers register hue hain!")
    
    LOGGER("Userbots").info("Starting userbots...")
    await load_userbots()
    
    LOGGER("PyTgCalls").info("Starting PyTgCalls...")
    from VCFIGHTERS.core.call import vc
    await vc.start()
    LOGGER("PyTgCalls").info("PyTgCalls ready")
    
    log.info("VCFIGHTER IS NOW ACTIVE - Ready to Destroy VCs")
    
    await idle()
    
    log.info("Shutting down...")
    try:
        from VCFIGHTERS.core.userbot import userbot_manager
        await userbot_manager.stop_all()
    except Exception:
        pass
    try:
        from VCFIGHTERS.core.call import vc
        await vc.stop_all()
    except Exception:
        pass
    await app.stop()
    log.info("Shutdown complete")

if __name__ == "__main__":
    asyncio.run(init())
    
