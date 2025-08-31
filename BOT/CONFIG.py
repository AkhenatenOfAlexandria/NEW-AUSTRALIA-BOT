import discord
import logging
from UTILS.CONFIGURATION import ANNOUNCEMENTS_ID, GENERAL_ID, MONEY_LOG_ID, intents, DEBUG_MODE

class BotConfig:
    VERSION = "v. Alpha 1.6.6"
    GUILD_ID = 574731470900559872
    GUILD = discord.Object(id=GUILD_ID)
    
    # Hospital configuration with better error handling
    HEALTH_LOG_ID = None
    HOSPITAL_TRANSPORT_COST = 1000
    HOSPITAL_HEALING_COST_PER_HP = 1000
    
    # Channel IDs
    ANNOUNCEMENTS_ID = ANNOUNCEMENTS_ID
    GENERAL_ID = GENERAL_ID
    MONEY_LOG_ID = MONEY_LOG_ID
    
    # Discord configuration
    intents = intents
    DEBUG_MODE = DEBUG_MODE

    def __init__(self):
        self._load_hospital_config()

    def _load_hospital_config(self):
        """Load hospital configuration with error handling"""
        try:
            from UTILS.CONFIGURATION import (
                HEALTH_LOG_ID as CONFIG_HEALTH_LOG_ID,
                HOSPITAL_TRANSPORT_COST as CONFIG_TRANSPORT_COST,
                HOSPITAL_HEALING_COST_PER_HP as CONFIG_HEALING_COST
            )
            self.HEALTH_LOG_ID = CONFIG_HEALTH_LOG_ID
            self.HOSPITAL_TRANSPORT_COST = CONFIG_TRANSPORT_COST
            self.HOSPITAL_HEALING_COST_PER_HP = CONFIG_HEALING_COST
            logging.info(f"✅ Hospital configuration loaded successfully")
            logging.info(f"✅ Health Log ID: {self.HEALTH_LOG_ID}")
            logging.info(f"✅ Transport Cost: {self.HOSPITAL_TRANSPORT_COST}")
            logging.info(f"✅ Healing Cost per HP: {self.HOSPITAL_HEALING_COST_PER_HP}")
        except ImportError as e:
            logging.warning(f"❌ Could not import hospital configuration: {e}")
            logging.warning(f"Using default values - Health Log: {self.HEALTH_LOG_ID}")
        except Exception as e:
            logging.error(f"❌ Unexpected error importing hospital configuration: {e}")
            logging.warning(f"Using default values - Health Log: {self.HEALTH_LOG_ID}")