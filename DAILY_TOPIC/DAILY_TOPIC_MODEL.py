import json
import os
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class DailyTopicData:
    """Handles data persistence and management for daily topics."""
    
    def __init__(self, data_file: str = "UTILS/daily_topics_data.json"):
        self.data_file = data_file
        self.data = self.load_data()
        self.default_topics = [
            "What's your favorite childhood memory?",
            "If you could have dinner with anyone, dead or alive, who would it be?",
            "What's the most interesting place you've ever visited?",
            "What skill would you most like to learn and why?",
            "What's your biggest goal for this year?",
            "If you could live in any time period, when would it be?",
            "What's the best advice you've ever received?",
            "What's your go-to comfort food?",
            "If you could instantly become an expert in something, what would it be?",
            "What's something you've learned recently that surprised you?",
            "What's your favorite way to spend a weekend?",
            "If you could change one thing about the world, what would it be?",
            "What's the most challenging thing you've ever done?",
            "What's your favorite book/movie and why?",
            "If you could have any superpower, what would it be?",
            "What's something you're grateful for today?",
            "What's the best gift you've ever given or received?",
            "If you could speak any language fluently, which would you choose?",
            "What's your ideal way to relax after a stressful day?",
            "What's something new you'd like to try this month?"
        ]
    
    def load_data(self) -> Dict[str, Any]:
        """Load data from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}
        return {}
    
    def save_data(self):
        """Save data to JSON file."""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error saving daily topics data: {e}")
    
    def get_guild_data(self, guild_id: int) -> Dict[str, Any]:
        """Get data for a specific guild."""
        guild_str = str(guild_id)
        if guild_str not in self.data:
            self.data[guild_str] = {
                "enabled": False,
                "channel_id": None,
                "role_id": None,
                "post_time": "09:00",
                "topics": self.default_topics.copy(),
                "used_topics": [],
                "pending_suggestions": [],
                "last_posted": None,
                "timezone": "UTC"
            }
            self.save_data()
        return self.data[guild_str]
    
    def initialize_guild_data(self, guilds):
        """Initialize default data structure for all guilds."""
        if not self.data:
            self.data = {}
        
        for guild in guilds:
            self.get_guild_data(guild.id)  # This will create default data if not exists
        self.save_data()