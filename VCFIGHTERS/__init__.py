from VCFIGHTERS.logging import LOGGER

LOGGER("VCFIGHTER").info("🔥 VCFIGHTER LOADING")

# Singletons import karo — naye mat banao
from VCFIGHTERS.core.bot import app
from VCFIGHTERS.core.userbot import userbot_manager
from VCFIGHTERS.core.call import vc
from VCFIGHTERS.database.mangodb import init_db

__version__ = "1.0.0"
