import logging
from discord.ext import commands
from SHEKELS.INCOME import INCOME
from UTILS.FUNCTIONS import BALANCE_UPDATED

class EventHandler:
    def __init__(self, bot):
        self.bot = bot
        self._register_events()

    def _register_events(self):
        """Register all event handlers"""
        @self.bot.event
        async def on_ready():
            await self._on_ready()

        @self.bot.event
        async def on_message(message):
            await self._on_message(message)

        @self.bot.event
        async def on_command_error(ctx, error):
            await self._on_command_error(ctx, error)

        @self.bot.event
        async def on_disconnect():
            await self._on_disconnect()

    async def _on_ready(self):
        """Handle bot ready event"""
        import discord
        from datetime import datetime
        
        logging.info(f'Logged in as {self.bot.user.name}.')
        await self.bot.change_presence(
            status=discord.Status.online,
            activity=discord.Game(name=self.bot.config.VERSION)
        )

        # Send startup message to Health Log if available
        hospital_system = self.bot.get_cog('HospitalSystem')
        if hospital_system:
            try:
                await hospital_system.core.send_info_to_health_log(
                    f"Bot {self.bot.user.name} is now online and operational. Version: {self.bot.config.VERSION}",
                    "🤖 Bot Online"
                )
            except Exception as e:
                logging.error(f"Failed to send startup message to health log: {e}")

        # Start task loops
        self.bot.task_manager.start_all_tasks()

    async def _on_message(self, message):
        """Handle message events"""
        logging.info(f'{message.created_at}: {message.author} sent message in #{message.channel}: "{message.content}"')
        
        if not message.author.bot:
            X = INCOME(message.author, message.channel)
            MONEY_LOG = self.bot.get_channel(self.bot.config.MONEY_LOG_ID)
            if X and MONEY_LOG:
                _MESSAGE = BALANCE_UPDATED(
                    TIME=message.created_at,
                    USER=message.author,
                    REASON="CHAT",
                    CASH=X,
                    MESSAGE=message
                )
                await MONEY_LOG.send(embed=_MESSAGE)
            try:
                await self.bot.process_commands(message)
            except Exception as e:
                logging.error(f"Error processing command: {e}")

    async def _on_command_error(self, ctx, error):
        """Handle command errors"""
        if isinstance(error, commands.CommandNotFound):
            return
        logging.error(f"Command error in {ctx.command}: {error}")

    async def _on_disconnect(self):
        """Handle bot disconnect"""
        logging.warning("Bot disconnected from Discord")
        
        hospital_system = self.bot.get_cog('HospitalSystem')
        if hospital_system:
            try:
                await hospital_system.core.send_warning_to_health_log(
                    "Bot has disconnected from Discord. Hospital services may be temporarily unavailable.",
                    "🔌 Bot Disconnected"
                )
            except Exception as e:
                logging.error(f"Failed to send disconnect message to health log: {e}")