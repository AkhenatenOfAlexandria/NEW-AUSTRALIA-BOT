# HEALING_LOGGER.py
import discord
import logging
from datetime import datetime

class HealingLogger:
    """Handles all healing-related logging"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def get_health_log_channel(self):
        """Get the health log channel with fallbacks"""
        # Try to find health log channel
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if 'health' in channel.name.lower() and 'log' in channel.name.lower():
                    return channel
                if channel.name.lower() in ['infirmary', 'hospital', 'healing']:
                    return channel
        
        # Fallback to general log channel
        for guild in self.bot.guilds:
            for channel in guild.text_channels:
                if 'log' in channel.name.lower():
                    return channel
        
        return None
    
    async def log_healing_action(self, user, action_type, **kwargs):
        """Log healing action to database and Discord"""
        # Create and send Discord embed
        embed = self._create_healing_embed(user, action_type, **kwargs)
        await self._send_to_health_log(embed)
    
    def _create_healing_embed(self, user, action_type, **kwargs):
        """Create Discord embed for healing action"""
        if action_type == "healing":
            embed = discord.Embed(
                title="🏥 Healing Transaction",
                description=f"{user.mention} has been healed!",
                color=discord.Color.green(),
                timestamp=datetime.utcnow()
            )
            embed.add_field(
                name="Health Restored", 
                value=f"{kwargs.get('health_healed', 0)} HP", 
                inline=True
            )
            embed.add_field(
                name="Cost", 
                value=f"{kwargs.get('cost', 0):,} shekels", 
                inline=True
            )
            embed.add_field(
                name="New Health", 
                value=f"{kwargs.get('new_health', 0)}/{kwargs.get('max_health', 100)} HP", 
                inline=True
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"User ID: {user.id}")
        
        return embed
    
    async def _send_to_health_log(self, embed):
        """Send embed to health log channel"""
        try:
            channel = await self.get_health_log_channel()
            if channel:
                await channel.send(embed=embed)
        except Exception as e:
            logging.error(f"Failed to send healing log: {e}")