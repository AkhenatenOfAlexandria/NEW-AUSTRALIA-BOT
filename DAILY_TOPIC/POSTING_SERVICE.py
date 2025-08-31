import discord
import logging
from datetime import datetime
from typing import Optional
from .DAILY_TOPIC_MODEL import DailyTopicData
from .DAILY_TOPIC_SERVICE import TopicService

logger = logging.getLogger(__name__)

class PostingService:
    """Handles posting daily topics to Discord channels."""
    
    def __init__(self, bot, data_manager: DailyTopicData, topic_service: TopicService):
        self.bot = bot
        self.data_manager = data_manager
        self.topic_service = topic_service
    
    async def post_daily_topic(self, guild_id: int) -> bool:
        """Post the daily topic for a guild."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return False
            
            guild_data = self.data_manager.get_guild_data(guild_id)
            
            channel = guild.get_channel(guild_data["channel_id"])
            role = guild.get_role(guild_data["role_id"])
            
            if not channel or not role:
                return False
            
            topic = self.topic_service.get_next_topic(guild_id)
            if not topic:
                return False
            
            embed = discord.Embed(
                title="📅 Daily Topic",
                description=topic,
                color=0x00FF7F,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Share your thoughts! Use /topic suggest to add new topics.")
            
            await channel.send(f"{role.mention}", embed=embed)
            
            guild_data["last_posted"] = datetime.now().strftime("%Y-%m-%d")
            self.data_manager.save_data()
            
            logger.info(f"Posted daily topic for guild {guild_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error posting daily topic for guild {guild_id}: {e}")
            return False
    
    def should_post_today(self, guild_id: int) -> bool:
        """Check if we should post today based on schedule."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        
        if not guild_data["enabled"] or not guild_data["channel_id"] or not guild_data["role_id"]:
            return False
        
        current_time = datetime.now()
        post_time_str = guild_data["post_time"]
        post_hour, post_minute = map(int, post_time_str.split(':'))
        
        last_posted = guild_data.get("last_posted")
        today = current_time.strftime("%Y-%m-%d")
        
        # Skip if already posted today
        if last_posted == today:
            return False
        
        # Check if it's the right time
        return current_time.hour == post_hour and current_time.minute >= post_minute