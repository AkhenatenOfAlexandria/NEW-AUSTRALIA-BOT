import random
from typing import Optional
from .DAILY_TOPIC_MODEL import DailyTopicData

class TopicService:
    """Handles topic selection and management logic."""
    
    def __init__(self, data_manager: DailyTopicData):
        self.data_manager = data_manager
    
    def get_next_topic(self, guild_id: int) -> Optional[str]:
        """Get the next topic for a guild."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        available_topics = [t for t in guild_data["topics"] if t not in guild_data["used_topics"]]
        
        # If all topics have been used, reset the used list
        if not available_topics:
            guild_data["used_topics"] = []
            available_topics = guild_data["topics"].copy()
            self.data_manager.save_data()
        
        if available_topics:
            topic = random.choice(available_topics)
            guild_data["used_topics"].append(topic)
            self.data_manager.save_data()
            return topic
        
        return None
    
    def add_topic(self, guild_id: int, topic: str) -> bool:
        """Add a topic to the guild's collection."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        
        if topic.lower() in [t.lower() for t in guild_data["topics"]]:
            return False
        
        guild_data["topics"].append(topic)
        self.data_manager.save_data()
        return True
    
    def remove_topic(self, guild_id: int, topic: str) -> bool:
        """Remove a topic from the guild's collection."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        original_count = len(guild_data["topics"])
        
        guild_data["topics"] = [t for t in guild_data["topics"] if t.lower() != topic.lower()]
        guild_data["used_topics"] = [t for t in guild_data["used_topics"] if t.lower() != topic.lower()]
        
        if len(guild_data["topics"]) < original_count:
            self.data_manager.save_data()
            return True
        return False
    
    def reset_used_topics(self, guild_id: int) -> int:
        """Reset used topics and return count of reset topics."""
        guild_data = self.data_manager.get_guild_data(guild_id)
        used_count = len(guild_data["used_topics"])
        guild_data["used_topics"] = []
        self.data_manager.save_data()
        return used_count