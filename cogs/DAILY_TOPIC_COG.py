from discord.ext import commands
from UTILS.CONFIGURATION import GUILD_ID

from DAILY_TOPIC.DAILY_TOPIC_MODEL import DailyTopicData
from DAILY_TOPIC.DAILY_TOPIC_SERVICE import TopicService
from DAILY_TOPIC.SUGGESTION_SERVICE import SuggestionService
from DAILY_TOPIC.POSTING_SERVICE import PostingService
from DAILY_TOPIC.DAILY_TOPIC_TASK import DailyTopicTask
from DAILY_TOPIC.DAILY_TOPIC_COMMANDS import DailyTopicCommands  # Fixed import path

class DailyTopics(commands.Cog):
    """A cog for managing daily discussion topics with customizable settings."""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize services
        self.data_manager = DailyTopicData()
        self.topic_service = TopicService(self.data_manager)
        self.suggestion_service = SuggestionService(self.data_manager)
        self.posting_service = PostingService(self.bot, self.data_manager, self.topic_service)
        
        # Initialize task
        self.task_manager = DailyTopicTask(self.bot, self.posting_service)
        
        # Initialize commands
        self.commands = DailyTopicCommands(
            self.bot, self.data_manager, self.topic_service, 
            self.suggestion_service, self.posting_service
        )
        
        # Start the task
        self.task_manager.start()
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.task_manager.stop()

async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(DailyTopics(bot))