import asyncio
import logging
import traceback
from discord.ext import tasks
from datetime import datetime

from FUNCTIONS import CALCULATE_DELAY
from SHEKELS.TAX import WEALTH_TAX
from SHEKELS.GAMES.STOCK_MARKET import STOCK_CHANGE

class TaskManager:
    def __init__(self, bot):
        self.bot = bot
        self._setup_tasks()

    def _setup_tasks(self):
        """Setup all scheduled tasks"""
        @tasks.loop(hours=168)  # Weekly
        async def treasury_update():
            await self._treasury_update()

        @tasks.loop(hours=1)  # Hourly
        async def stock_update():
            await self._stock_update()

        @tasks.loop(minutes=5)  # Every 5 minutes
        async def hospital_update():
            await self._hospital_update()

        # Error handlers
        @treasury_update.error
        async def treasury_update_error(error):
            logging.error(f"❌ Treasury update loop error: {error}")

        @stock_update.error
        async def stock_update_error(error):
            logging.error(f"❌ Stock update loop error: {error}")

        @hospital_update.error
        async def hospital_update_error(error):
            await self._handle_hospital_error(error)

        self.treasury_update = treasury_update
        self.stock_update = stock_update
        self.hospital_update = hospital_update

    def start_all_tasks(self):
        """Start all scheduled tasks with delays"""
        asyncio.create_task(self._delayed_start(
            self.stock_update,
            CALCULATE_DELAY("HOURLY"),
            "STOCK_UPDATE"
        ))
        asyncio.create_task(self._delayed_start(
            self.treasury_update,
            CALCULATE_DELAY("WEEKLY"),
            "TREASURY_UPDATE"
        ))
        asyncio.create_task(self._delayed_start(
            self.hospital_update,
            CALCULATE_DELAY("EVERY_5_MINUTES"),
            "HOSPITAL_UPDATE"
        ))
        # Optional: immediate pass so users are processed at boot
        asyncio.create_task(self._hospital_update())

    async def _delayed_start(self, loop_task, delay_seconds: float, name: str):
        """Start a task loop with delay"""
        try:
            if delay_seconds and delay_seconds > 0:
                logging.info(f"{name}: sleeping {delay_seconds:.2f}s before start")
                await asyncio.sleep(delay_seconds)
            if not loop_task.is_running():
                loop_task.start()
                logging.info(f"{name}: started")
            else:
                logging.info(f"{name}: already running; skip start")
        except Exception as e:
            logging.error(f"{name}: failed to start: {e}", exc_info=True)

    async def _treasury_update(self):
        """Collect wealth tax from rich users"""
        ANNOUNCEMENTS = self.bot.get_channel(self.bot.config.ANNOUNCEMENTS_ID)
        if ANNOUNCEMENTS:
            await ANNOUNCEMENTS.send(f"Wealth Tax collected:\n{WEALTH_TAX()}")
        else:
            logging.error("ANNOUNCEMENTS CHANNEL NOT FOUND.")

    async def _stock_update(self):
        """Update stock market prices"""
        STOCK_CHANGE()
        STRING = "Stock Prices have been updated. Use /stockmarket to view them."
        MONEY_LOG = self.bot.get_channel(self.bot.config.MONEY_LOG_ID)
        if MONEY_LOG:
            await MONEY_LOG.send(STRING)
        else:
            logging.error("MONEY_LOG CHANNEL NOT FOUND.")

    async def _hospital_update(self):
        """Process unconscious users for hospital transport and healing"""
        logging.debug("HOSPITAL_UPDATE() Activated.")
        
        hospital_system = self.bot.get_cog('HospitalSystem')
        if hospital_system:
            # Send cycle start message
            try:
                await hospital_system.core.send_text_to_health_log(
                    "Automatic hospital cycle triggered by scheduled task",
                    "⏰ Scheduled Hospital Update"
                )
            except Exception as log_error:
                logging.error(f"Failed to log hospital cycle start: {log_error}")
            
            try:
                await hospital_system.process_unconscious_users()
            except Exception as e:
                logging.error(f"❌ Error in hospital update: {e}")
                
                # Send error to health log
                try:
                    await hospital_system.core.send_error_to_health_log(
                        f"Hospital update cycle failed: {str(e)}",
                        f"Automatic hospital cycle encountered an error: {traceback.format_exc()}"
                    )
                except Exception as log_error:
                    logging.error(f"❌ Failed to log hospital error to health log: {log_error}")
                    
                traceback.print_exc()
        else:
            logging.warning("HospitalSystem cog not found - skipping hospital update")
            await self._log_hospital_system_error()

    async def _log_hospital_system_error(self):
        """Log hospital system not found error"""
        try:
            import discord
            HEALTH_LOG = self.bot.get_channel(self.bot.config.HEALTH_LOG_ID) if self.bot.config.HEALTH_LOG_ID else None
            if HEALTH_LOG:
                embed = discord.Embed(
                    title="❌ Hospital System Error", 
                    description="HospitalSystem cog not found - medical services unavailable",
                    color=0xff0000,
                    timestamp=datetime.now()
                )
                await HEALTH_LOG.send(embed=embed)
        except Exception as e:
            logging.error(f"Failed to send hospital system error to health log: {e}")

    async def _handle_hospital_error(self, error):
        """Handle errors in the hospital update loop"""
        logging.error(f"❌ Hospital update loop error: {error}")
        
        hospital_system = self.bot.get_cog('HospitalSystem')
        if hospital_system:
            try:
                await hospital_system.core.send_error_to_health_log(
                    f"Hospital update loop encountered an error: {str(error)}",
                    f"The scheduled hospital update task failed: {traceback.format_exc()}"
                )
            except Exception as log_error:
                logging.error(f"Failed to log hospital loop error to health log: {log_error}")