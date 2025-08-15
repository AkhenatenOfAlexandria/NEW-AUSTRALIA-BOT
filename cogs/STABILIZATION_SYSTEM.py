import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

# Import configurations
try:
    from UTILS.CONFIGURATION import GUILD_ID
except ImportError:
    # Fallback - replace with your actual guild ID
    GUILD_ID = 123456789

from .STABILIZATION.STABILIZATION_MANAGER import StabilizationManager

GUILD = discord.Object(id=GUILD_ID)

class StabilizationCog(commands.Cog):
    """Discord cog for stabilization system commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.manager = StabilizationManager(bot)
        
        # Initialize the stabilization system
        try:
            self.manager.initialize()
            logging.info("✅ Stabilization Cog initialized successfully")
        except Exception as e:
            logging.error(f"❌ Failed to initialize Stabilization Cog: {e}")
            raise
    
    async def cog_unload(self):
        """Clean shutdown when cog is unloaded"""
        try:
            self.manager.shutdown()
            logging.info("⚠️ Stabilization Cog unloaded")
        except Exception as e:
            logging.error(f"Error unloading Stabilization Cog: {e}")
    
    # Slash Commands
    
    @app_commands.command(
        name="stabilization_status", 
        description="Check stabilization status for yourself or another user"
    )
    @app_commands.guilds(GUILD)
    @app_commands.describe(user="User to check (leave empty for yourself)")
    async def stabilization_status(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.Member] = None
    ):
        """Check stabilization status"""
        await self.manager.show_stabilization_status(interaction, user)
    
    # Debug Commands (remove these in production or restrict to admin)
    
    @app_commands.command(
        name="debug_start_stabilization", 
        description="[DEBUG] Force start stabilization for testing"
    )
    @app_commands.guilds(GUILD)
    @app_commands.describe(user="User to start stabilization for (leave empty for yourself)")
    async def debug_start_stabilization(
        self, 
        interaction: discord.Interaction, 
        user: Optional[discord.Member] = None
    ):
        """Debug command to start stabilization"""
        await self.manager.debug_start_stabilization(interaction, user)
    
    @app_commands.command(
        name="debug_damage", 
        description="[DEBUG] Apply damage for testing"
    )
    @app_commands.guilds(GUILD)
    @app_commands.describe(
        amount="Amount of damage to apply",
        user="User to damage (leave empty for yourself)"
    )
    async def debug_damage(
        self, 
        interaction: discord.Interaction, 
        amount: int, 
        user: Optional[discord.Member] = None
    ):
        """Debug command to apply damage"""
        if amount <= 0:
            await interaction.response.send_message(
                "❌ Damage amount must be positive!", 
                ephemeral=True
            )
            return
        
        await self.manager.debug_damage(interaction, amount, user)
    
    # Public API methods for other cogs to use
    
    def start_stabilization(self, user_id: int) -> bool:
        """Start stabilization for a user (called by other systems)"""
        return self.manager.start_stabilization(user_id)
    
    def add_stabilization_failure(self, user_id: int, count: int = 1) -> str:
        """Add stabilization failures (called when user takes damage)"""
        return self.manager.add_stabilization_failure(user_id, count)
    
    def is_user_stabilizing(self, user_id: int) -> bool:
        """Check if user is currently stabilizing"""
        return self.manager.is_user_stabilizing(user_id)
    
    def get_stabilization_status(self, user_id: int):
        """Get user's stabilization status"""
        return self.manager.get_stabilization_status(user_id)

async def setup(bot):
    """Required function for Discord.py to load the cog"""
    try:
        await bot.add_cog(StabilizationCog(bot))
        logging.info("✅ Stabilization Cog loaded successfully")
    except Exception as e:
        logging.error(f"❌ Failed to load Stabilization Cog: {e}")
        raise