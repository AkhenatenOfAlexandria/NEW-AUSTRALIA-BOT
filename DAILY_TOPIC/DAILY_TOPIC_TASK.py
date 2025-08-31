import logging
from discord.ext import tasks
from .POSTING_SERVICE import PostingService

logger = logging.getLogger(__name__)

class DailyTopicTask:
    """Handles the scheduled posting of daily topics."""
    
    def __init__(self, bot, posting_service: PostingService):
        self.bot = bot
        self.posting_service = posting_service
    
    @tasks.loop(minutes=30)
    async def daily_topic_task(self):
        """Task that runs to post daily topics."""
        for guild in self.bot.guilds:
            try:
                if self.posting_service.should_post_today(guild.id):
                    await self.posting_service.post_daily_topic(guild.id)
            except Exception as e:
                logger.error(f"Error in daily topic task for guild {guild.id}: {e}")
    
    @daily_topic_task.before_loop
    async def before_daily_topic_task(self):
        """Wait for the bot to be ready before starting the task."""
        await self.bot.wait_until_ready()
    
    def start(self):
        """Start the task."""
        self.daily_topic_task.start()
    
    def stop(self):
        """Stop the task."""
        self.daily_topic_task.cancel()