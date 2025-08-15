import discord
import json
import os
import random
import asyncio
import logging
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime
from typing import Optional, Dict, Any


from UTILS.CONFIGURATION import GUILD_ID

logger = logging.getLogger(__name__)

class DailyTopics(commands.Cog):
    """A cog for managing daily discussion topics with customizable settings."""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_file = "daily_topics_data.json"
        self.data = self.load_data()
        
        # Default topics if none exist
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
        
        # Initialize default data structure if needed
        self.initialize_default_data()
        
        # Start the daily topic task
        self.daily_topic_task.start()
    
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
    
    def initialize_default_data(self):
        """Initialize default data structure for guilds."""
        if not self.data:
            self.data = {}
        
        # Ensure each guild has a proper data structure
        for guild in self.bot.guilds:
            guild_id = str(guild.id)
            if guild_id not in self.data:
                self.data[guild_id] = {
                    "enabled": False,
                    "channel_id": None,
                    "role_id": None,
                    "post_time": "09:00",  # 9 AM
                    "topics": self.default_topics.copy(),
                    "used_topics": [],
                    "pending_suggestions": [],
                    "last_posted": None,
                    "timezone": "UTC"
                }
        self.save_data()
    
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
    
    def get_next_topic(self, guild_id: int) -> Optional[str]:
        """Get the next topic for a guild."""
        guild_data = self.get_guild_data(guild_id)
        available_topics = [t for t in guild_data["topics"] if t not in guild_data["used_topics"]]
        
        # If all topics have been used, reset the used list
        if not available_topics:
            guild_data["used_topics"] = []
            available_topics = guild_data["topics"].copy()
            self.save_data()
        
        if available_topics:
            topic = random.choice(available_topics)
            guild_data["used_topics"].append(topic)
            self.save_data()
            return topic
        
        return None
    
    @tasks.loop(minutes=30)  # Check every 30 minutes
    async def daily_topic_task(self):
        """Task that runs to post daily topics."""
        current_time = datetime.now()
        
        for guild in self.bot.guilds:
            try:
                guild_data = self.get_guild_data(guild.id)
                
                # Skip if not enabled
                if not guild_data["enabled"]:
                    continue
                
                # Skip if no channel or role configured
                if not guild_data["channel_id"] or not guild_data["role_id"]:
                    continue
                
                # Check if it's time to post
                post_time_str = guild_data["post_time"]
                post_hour, post_minute = map(int, post_time_str.split(':'))
                
                # Check if we should post today
                last_posted = guild_data.get("last_posted")
                today = current_time.strftime("%Y-%m-%d")
                
                # Skip if already posted today
                if last_posted == today:
                    continue
                
                # Check if it's the right time
                if current_time.hour == post_hour and current_time.minute >= post_minute:
                    await self.post_daily_topic(guild.id)
                    
            except Exception as e:
                logger.error(f"Error in daily topic task for guild {guild.id}: {e}")
    
    async def post_daily_topic(self, guild_id: int):
        """Post the daily topic for a guild."""
        try:
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return
            
            guild_data = self.get_guild_data(guild_id)
            
            channel = guild.get_channel(guild_data["channel_id"])
            role = guild.get_role(guild_data["role_id"])
            
            if not channel or not role:
                return
            
            topic = self.get_next_topic(guild_id)
            if not topic:
                return
            
            # Create embed
            embed = discord.Embed(
                title="📅 Daily Topic",
                description=topic,
                color=0x00FF7F,
                timestamp=datetime.now()
            )
            embed.set_footer(text="Share your thoughts! Use /topic suggest to add new topics.")
            
            # Post the topic
            await channel.send(f"{role.mention}", embed=embed)
            
            # Update last posted date
            guild_data["last_posted"] = datetime.now().strftime("%Y-%m-%d")
            self.save_data()
            
            logger.info(f"Posted daily topic for guild {guild_id}")
            
        except Exception as e:
            logger.error(f"Error posting daily topic for guild {guild_id}: {e}")
    
    @daily_topic_task.before_loop
    async def before_daily_topic_task(self):
        """Wait for the bot to be ready before starting the task."""
        await self.bot.wait_until_ready()
        # Initialize data for all guilds
        self.initialize_default_data()
    
    # Slash command group
    topic_group = app_commands.Group(name="topic", description="Daily topic management")
    
    @topic_group.command(name="setup", description="Set up daily topics for this server (Admin only)")
    @app_commands.describe(
        channel="Channel where topics will be posted",
        role="Role to ping with daily topics",
        time="Time to post daily topics (format: HH:MM, 24-hour)"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup(
        self, 
        interaction: discord.Interaction, 
        channel: discord.TextChannel,
        role: discord.Role,
        time: str = "09:00"
    ):
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
        
        guild_data = self.get_guild_data(interaction.guild.id)
        guild_data["enabled"] = True
        guild_data["channel_id"] = channel.id
        guild_data["role_id"] = role.id
        guild_data["post_time"] = time
        self.save_data()
        
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
    
    @topic_group.command(name="disable", description="Disable daily topics (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def disable(self, interaction: discord.Interaction):
        """Disable daily topics for the server."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        guild_data["enabled"] = False
        self.save_data()
        
        embed = discord.Embed(
            title="🔴 Daily Topics Disabled",
            description="Daily topics have been disabled for this server.",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed)
    
    @topic_group.command(name="suggest", description="Suggest a new daily topic")
    @app_commands.describe(topic="Your suggested discussion topic")
    async def suggest(self, interaction: discord.Interaction, topic: str):
        """Suggest a new daily topic."""
        
        if len(topic) < 10:
            await interaction.response.send_message(
                "❌ Please provide a topic that's at least 10 characters long!",
                ephemeral=True
            )
            return
        
        if len(topic) > 500:
            await interaction.response.send_message(
                "❌ Please keep your topic suggestion under 500 characters!",
                ephemeral=True
            )
            return
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        # Check if topic already exists
        if topic.lower() in [t.lower() for t in guild_data["topics"]]:
            await interaction.response.send_message(
                "❌ This topic already exists in our collection!",
                ephemeral=True
            )
            return
        
        # Check if already in pending suggestions
        if topic.lower() in [s["topic"].lower() for s in guild_data["pending_suggestions"]]:
            await interaction.response.send_message(
                "❌ This topic has already been suggested and is pending review!",
                ephemeral=True
            )
            return
        
        # Add to pending suggestions
        suggestion = {
            "topic": topic,
            "suggested_by": interaction.user.id,
            "suggested_at": datetime.now().isoformat(),
            "status": "pending"
        }
        guild_data["pending_suggestions"].append(suggestion)
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Topic Suggested",
            description=f"Your topic suggestion has been submitted for review:\n\n*{topic}*",
            color=0x00FF00
        )
        embed.set_footer(text="Administrators can review suggestions using /topic review")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @topic_group.command(name="review", description="Review pending topic suggestions (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def review(self, interaction: discord.Interaction):
        """Review pending topic suggestions."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        pending = [s for s in guild_data["pending_suggestions"] if s["status"] == "pending"]
        
        if not pending:
            await interaction.response.send_message(
                "📝 No pending topic suggestions to review!",
                ephemeral=True
            )
            return
        
        # Create embed with pending suggestions
        embed = discord.Embed(
            title="📋 Pending Topic Suggestions",
            description=f"There are {len(pending)} suggestions awaiting review.",
            color=0x2F3136
        )
        
        for i, suggestion in enumerate(pending[:5], 1):  # Show first 5
            user = self.bot.get_user(suggestion["suggested_by"])
            username = user.display_name if user else "Unknown User"
            suggested_date = datetime.fromisoformat(suggestion["suggested_at"]).strftime("%Y-%m-%d")
            
            embed.add_field(
                name=f"{i}. By {username}",
                value=f"*{suggestion['topic']}*\n📅 {suggested_date}",
                inline=False
            )
        
        if len(pending) > 5:
            embed.set_footer(text=f"Showing 5 of {len(pending)} suggestions. Use /topic approve or /topic reject to manage them.")
        else:
            embed.set_footer(text="Use /topic approve or /topic reject to manage suggestions.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @topic_group.command(name="approve", description="Approve a topic suggestion (Admin only)")
    @app_commands.describe(topic="The exact topic text to approve")
    @app_commands.default_permissions(administrator=True)
    async def approve(self, interaction: discord.Interaction, topic: str):
        """Approve a topic suggestion."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        # Find the suggestion
        suggestion = None
        for s in guild_data["pending_suggestions"]:
            if s["topic"].lower() == topic.lower() and s["status"] == "pending":
                suggestion = s
                break
        
        if not suggestion:
            await interaction.response.send_message(
                "❌ Could not find a pending suggestion with that exact text!",
                ephemeral=True
            )
            return
        
        # Add to topics and mark as approved
        guild_data["topics"].append(suggestion["topic"])
        suggestion["status"] = "approved"
        suggestion["approved_by"] = interaction.user.id
        suggestion["approved_at"] = datetime.now().isoformat()
        self.save_data()
        
        # Notify the suggester if possible
        user = self.bot.get_user(suggestion["suggested_by"])
        if user:
            try:
                dm_embed = discord.Embed(
                    title="✅ Topic Suggestion Approved",
                    description=f"Your suggested topic has been approved and added to the daily topics:\n\n*{suggestion['topic']}*",
                    color=0x00FF00
                )
                dm_embed.set_footer(text=f"Approved in {interaction.guild.name}")
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
        
        embed = discord.Embed(
            title="✅ Topic Approved",
            description=f"The following topic has been added to the daily topics:\n\n*{suggestion['topic']}*",
            color=0x00FF00
        )
        embed.add_field(name="Total Topics", value=str(len(guild_data["topics"])), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @topic_group.command(name="reject", description="Reject a topic suggestion (Admin only)")
    @app_commands.describe(
        topic="The exact topic text to reject",
        reason="Optional reason for rejection"
    )
    @app_commands.default_permissions(administrator=True)
    async def reject(self, interaction: discord.Interaction, topic: str, reason: str = None):
        """Reject a topic suggestion."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        # Find the suggestion
        suggestion = None
        for s in guild_data["pending_suggestions"]:
            if s["topic"].lower() == topic.lower() and s["status"] == "pending":
                suggestion = s
                break
        
        if not suggestion:
            await interaction.response.send_message(
                "❌ Could not find a pending suggestion with that exact text!",
                ephemeral=True
            )
            return
        
        # Mark as rejected
        suggestion["status"] = "rejected"
        suggestion["rejected_by"] = interaction.user.id
        suggestion["rejected_at"] = datetime.now().isoformat()
        if reason:
            suggestion["rejection_reason"] = reason
        self.save_data()
        
        # Notify the suggester if possible
        user = self.bot.get_user(suggestion["suggested_by"])
        if user:
            try:
                dm_embed = discord.Embed(
                    title="❌ Topic Suggestion Rejected",
                    description=f"Your suggested topic was not approved:\n\n*{suggestion['topic']}*",
                    color=0xFF0000
                )
                if reason:
                    dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.set_footer(text=f"From {interaction.guild.name}")
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                pass  # User has DMs disabled
        
        embed = discord.Embed(
            title="❌ Topic Rejected",
            description=f"The following topic suggestion has been rejected:\n\n*{suggestion['topic']}*",
            color=0xFF0000
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @topic_group.command(name="add", description="Directly add a topic to the collection (Admin only)")
    @app_commands.describe(topic="The topic to add")
    @app_commands.default_permissions(administrator=True)
    async def add_topic(self, interaction: discord.Interaction, topic: str):
        """Directly add a topic to the collection."""
        
        if len(topic) < 10:
            await interaction.response.send_message(
                "❌ Please provide a topic that's at least 10 characters long!",
                ephemeral=True
            )
            return
        
        if len(topic) > 500:
            await interaction.response.send_message(
                "❌ Please keep topics under 500 characters!",
                ephemeral=True
            )
            return
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        # Check if topic already exists
        if topic.lower() in [t.lower() for t in guild_data["topics"]]:
            await interaction.response.send_message(
                "❌ This topic already exists in the collection!",
                ephemeral=True
            )
            return
        
        guild_data["topics"].append(topic)
        self.save_data()
        
        embed = discord.Embed(
            title="✅ Topic Added",
            description=f"New topic added to the collection:\n\n*{topic}*",
            color=0x00FF00
        )
        embed.add_field(name="Total Topics", value=str(len(guild_data["topics"])), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @topic_group.command(name="remove", description="Remove a topic from the collection (Admin only)")
    @app_commands.describe(topic="The exact topic text to remove")
    @app_commands.default_permissions(administrator=True)
    async def remove_topic(self, interaction: discord.Interaction, topic: str):
        """Remove a topic from the collection."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        # Find and remove the topic
        original_count = len(guild_data["topics"])
        guild_data["topics"] = [t for t in guild_data["topics"] if t.lower() != topic.lower()]
        
        if len(guild_data["topics"]) == original_count:
            await interaction.response.send_message(
                "❌ Could not find a topic with that exact text!",
                ephemeral=True
            )
            return
        
        # Also remove from used topics if present
        guild_data["used_topics"] = [t for t in guild_data["used_topics"] if t.lower() != topic.lower()]
        self.save_data()
        
        embed = discord.Embed(
            title="🗑️ Topic Removed",
            description=f"Removed topic from collection:\n\n*{topic}*",
            color=0xFF0000
        )
        embed.add_field(name="Remaining Topics", value=str(len(guild_data["topics"])), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @topic_group.command(name="list", description="List all topics or show statistics (Admin only)")
    @app_commands.describe(show_all="Whether to show all topics (default: just statistics)")
    @app_commands.default_permissions(administrator=True)
    async def list_topics(self, interaction: discord.Interaction, show_all: bool = False):
        """List all topics or show statistics."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        if not show_all:
            # Just show statistics
            embed = discord.Embed(
                title="📊 Daily Topics Statistics",
                color=0x2F3136
            )
            embed.add_field(name="Total Topics", value=str(len(guild_data["topics"])), inline=True)
            embed.add_field(name="Used Topics", value=str(len(guild_data["used_topics"])), inline=True)
            embed.add_field(name="Remaining", value=str(len(guild_data["topics"]) - len(guild_data["used_topics"])), inline=True)
            embed.add_field(name="Pending Suggestions", value=str(len([s for s in guild_data["pending_suggestions"] if s["status"] == "pending"])), inline=True)
            embed.add_field(name="Status", value="✅ Enabled" if guild_data["enabled"] else "❌ Disabled", inline=True)
            embed.add_field(name="Post Time", value=f"{guild_data['post_time']} UTC", inline=True)
            
            if guild_data["last_posted"]:
                embed.add_field(name="Last Posted", value=guild_data["last_posted"], inline=True)
            
            embed.set_footer(text="Use show_all=True to see all topics")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        else:
            # Show all topics (paginated if needed)
            topics = guild_data["topics"]
            if not topics:
                await interaction.response.send_message("❌ No topics found!", ephemeral=True)
                return
            
            # Split into chunks of 10 topics per embed
            chunk_size = 10
            chunks = [topics[i:i + chunk_size] for i in range(0, len(topics), chunk_size)]
            
            embeds = []
            for i, chunk in enumerate(chunks, 1):
                embed = discord.Embed(
                    title=f"📝 All Topics (Page {i}/{len(chunks)})",
                    color=0x2F3136
                )
                
                topic_list = "\n".join([f"{j + (i-1)*chunk_size + 1}. {topic}" for j, topic in enumerate(chunk)])
                embed.description = topic_list
                
                embed.set_footer(text=f"Total: {len(topics)} topics")
                embeds.append(embed)
            
            # Send first embed
            await interaction.response.send_message(embed=embeds[0], ephemeral=True)
            
            # Send additional embeds if needed
            for embed in embeds[1:]:
                await interaction.followup.send(embed=embed, ephemeral=True)
    
    @topic_group.command(name="post", description="Manually post today's topic (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def manual_post(self, interaction: discord.Interaction):
        """Manually post today's topic."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        
        if not guild_data["enabled"]:
            await interaction.response.send_message(
                "❌ Daily topics are not enabled! Use `/topic setup` first.",
                ephemeral=True
            )
            return
        
        if not guild_data["channel_id"] or not guild_data["role_id"]:
            await interaction.response.send_message(
                "❌ Daily topics are not properly configured! Use `/topic setup` first.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer()
        
        try:
            await self.post_daily_topic(interaction.guild.id)
            await interaction.followup.send("✅ Daily topic posted successfully!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to post daily topic: {str(e)}")
    
    @topic_group.command(name="reset", description="Reset used topics to start over (Admin only)")
    @app_commands.default_permissions(administrator=True)
    async def reset_used(self, interaction: discord.Interaction):
        """Reset the used topics list."""
        
        guild_data = self.get_guild_data(interaction.guild.id)
        used_count = len(guild_data["used_topics"])
        guild_data["used_topics"] = []
        self.save_data()
        
        embed = discord.Embed(
            title="🔄 Topics Reset",
            description=f"Reset {used_count} used topics. All topics are now available again!",
            color=0x00FF00
        )
        embed.add_field(name="Available Topics", value=str(len(guild_data["topics"])), inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    def cog_unload(self):
        """Clean up when the cog is unloaded."""
        self.daily_topic_task.cancel()

async def setup(bot):
    """Setup function to add the cog to the bot."""
    await bot.add_cog(DailyTopics(bot))
    
    # Sync the slash commands to your guild
    guild = discord.Object(id=GUILD_ID)
    bot.tree.add_command(DailyTopics(bot).topic_group, guild=guild)