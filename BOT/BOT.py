import asyncio
import logging
import traceback

from discord.ext import commands
from datetime import datetime

from .CONFIG import BotConfig
from .EVENTS import EventHandler
from .TASKS import TaskManager
from .DEBUG_COMMANDS import DebugCommands
from .HOSPITAL_INTEGRATION import HospitalIntegration

from UTILS.TOKEN import TOKEN

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

class NewAustraliaBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="$",
            intents=BotConfig.intents,
        )
        
        # Initialize components
        self.config = BotConfig()
        self.event_handler = EventHandler(self)
        self.task_manager = TaskManager(self)
        self.debug_commands = DebugCommands(self)
        self.hospital_integration = HospitalIntegration(self)
        
        # Set log IDs
        self.HEALTH_LOG_ID = self.config.HEALTH_LOG_ID
        self.MONEY_LOG_ID = self.config.MONEY_LOG_ID
        
        logging.info(f"🏥 Bot initialized with Health Log ID: {self.HEALTH_LOG_ID}")
        logging.info(f"💰 Bot initialized with Money Log ID: {self.MONEY_LOG_ID}")

    async def setup_hook(self):
        """Setup hook for bot initialization"""
        await self._load_cogs()
        await self._sync_commands()

    async def _load_cogs(self):
        """Load all cogs with enhanced logging"""
        from pathlib import Path
        
        loaded_cogs = []
        failed_cogs = []
        
        cog_files = list((Path(__file__).parent.parent/"cogs").glob("*.py"))
        logging.info(f"Found {len(cog_files)} potential cog files")
        
        for file in cog_files:
            if not file.name.startswith("_"):
                cog_name = file.stem
                extension_name = f"cogs.{cog_name}"
                
                logging.info(f"Attempting to load: {cog_name}")
                try:
                    if cog_name in [cog.__class__.__name__ for cog in self.cogs.values()]:
                        logging.info(f"🔄 Cog {cog_name} already loaded, reloading...")
                        await self.reload_extension(extension_name)
                    else:
                        await self.load_extension(extension_name)
                    
                    loaded_cogs.append(cog_name)
                    logging.info(f"✅ Successfully loaded cog: {cog_name}")
                    
                except commands.ExtensionAlreadyLoaded:
                    logging.info(f"🔄 Reloading already loaded cog: {cog_name}")
                    try:
                        await self.reload_extension(extension_name)
                        loaded_cogs.append(cog_name)
                        logging.info(f"✅ Successfully reloaded cog: {cog_name}")
                    except Exception as e:
                        failed_cogs.append(cog_name)
                        logging.error(f"❌ Failed to reload cog {cog_name}: {e}")
                        
                except Exception as e:
                    failed_cogs.append(cog_name)
                    logging.error(f"❌ Failed to load cog {cog_name}: {e}")
                    traceback.print_exc()

        logging.info(f"Successfully loaded: {loaded_cogs}")
        logging.info(f"Failed to load: {failed_cogs}")
        logging.info(f"Total cogs loaded: {len(loaded_cogs)}")

    async def _sync_commands(self):
        """Sync slash commands if not in debug mode"""
        if not self.config.DEBUG_MODE:
            try:
                logging.info("Getting commands before sync...")
                guild_commands_before = self.tree.get_commands(guild=self.config.GUILD)
                
                logging.info(f"Guild commands before sync: {len(guild_commands_before)}")
                
                if guild_commands_before:
                    guild_names = [cmd.name for cmd in guild_commands_before]
                    logging.info(f"Guild command names: {guild_names}")
                
                logging.info("Clearing existing guild commands...")
                self.tree.clear_commands(guild=self.config.GUILD)
                
                logging.info("Copying cog commands to tree...")
                for cog in self.cogs.values():
                    for command in cog.get_app_commands():
                        logging.info(f"Adding command to tree: {command.name}")
                        self.tree.add_command(command, guild=self.config.GUILD)
                
                commands_in_tree = self.tree.get_commands(guild=self.config.GUILD)
                logging.info(f"Commands in tree before sync: {len(commands_in_tree)}")
                for cmd in commands_in_tree:
                    logging.info(f"  - {cmd.name}")
                
                logging.info("Syncing guild commands...")
                synced = await asyncio.wait_for(
                    self.tree.sync(guild=self.config.GUILD), 
                    timeout=30.0
                )
                logging.info(f"Successfully synced {len(synced)} guild commands")
                
                for cmd in synced:
                    logging.info(f"Synced command: {cmd.name}")
                    
            except asyncio.TimeoutError:
                logging.error("Command sync timed out after 30 seconds - continuing startup")
            except Exception as e:
                logging.error(f"Failed to sync commands: {e}")
                traceback.print_exc()
        else:
            logging.info("🔧 DEBUG MODE: Skipping command sync to avoid rate limits")

    def run_bot(self):
        """Run the bot with token"""
        logging.info("Starting bot...")
        self.run(TOKEN)