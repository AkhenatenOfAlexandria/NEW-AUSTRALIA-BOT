import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
from typing import Optional

class DailyTopicCommands:
    """Discord commands for daily topic management."""
    
    def __init__(self, bot, data_manager, topic_service, suggestion_service, posting_service):
        self.bot = bot
        self.data_manager = data_manager
        self.topic_service = topic_service
        self.suggestion_service = suggestion_service
        self.posting_service = posting_service
        
        # Create the command group
        self.topic_group = app_commands.Group(name="topic", description="Daily topic management")
        
        # Add commands to the group
        self.topic_group.command(name="setup", description="Set up daily topics for this server (Admin only)")(self.setup)
    
    @app_commands.describe(
        channel="Channel where topics will be posted",
        role="Role to ping with daily topics", 
        time="Time to post daily topics (format: HH:MM, 24-hour)"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(self, interaction: discord.Interaction, 
                   channel: discord.TextChannel,
                   role: discord.Role, 
                   time: str = "09:00"):
        """Set up daily topics for the server."""
        
        # Validate time format
        try:
            time_parts = time.split(':')
            if len(time_parts) != 2:
                raise ValueError("Invalid time format")
            hour, minute = map(int, time_parts)
            if not (0 <= hour <= 23) or not (0 <= minute <= 59):
                raise ValueError("Invalid time values")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid time format! Please use HH:MM format (24-hour), e.g., 09:00 or 14:30",
                ephemeral=True
            )
            return
        
        # Check bot permissions
        if not channel.permissions_for(interaction.guild.me).send_messages:
            await interaction.response.send_message(
                f"❌ I don't have permission to send messages in {channel.mention}!",
                ephemeral=True
            )
            return
        
        guild_data = self.data_manager.get_guild_data(interaction.guild.id)
        guild_data["enabled"] = True
        guild_data["channel_id"] = channel.id
        guild_data["role_id"] = role.id
        guild_data["post_time"] = time
        self.data_manager.save_data()
        
        embed = discord.Embed(
            title="✅ Daily Topics Configured",
            color=0x00FF00
        )
        embed.add_field(name="Channel", value=channel.mention, inline=True)
        embed.add_field(name="Role", value=role.mention, inline=True)
        embed.add_field(name="Post Time", value=f"{time} UTC", inline=True)
        embed.add_field(name="Topics Available", value=str(len(guild_data["topics"])), inline=True)
        embed.set_footer(text="Daily topics are now enabled!")
        
        await interaction.response.send_message(embed=embed)