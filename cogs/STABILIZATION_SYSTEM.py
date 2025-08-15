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
    
    @app_commands.command(
        name="debug_system_health", 
        description="[DEBUG] Check stabilization system health"
    )
    @app_commands.guilds(GUILD)
    async def debug_system_health(
        self, 
        interaction: discord.Interaction
    ):
        """Debug command to check system health"""
        await self.manager.debug_system_health(interaction)
    
    @app_commands.command(
        name="debug_restart_stabilization", 
        description="[DEBUG] Restart the stabilization system"
    )
    @app_commands.guilds(GUILD)
    async def debug_restart_stabilization(
        self, 
        interaction: discord.Interaction
    ):
        """Debug command to restart the stabilization system"""
        await self.manager.debug_restart_system(interaction)
    
    # Bot event handlers
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Handle bot ready event - check if system needs restart"""
        try:
            health_status = self.manager.check_system_health()
            if not health_status.get('healthy'):
                logging.warning("Stabilization system unhealthy on bot ready, attempting restart...")
                self.manager.restart_system()
        except Exception as e:
            logging.error(f"Error checking stabilization system on ready: {e}")
    
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
    
    @app_commands.command(name="debug_stabilization_db", description="Debug stabilization database")
    @app_commands.guilds(GUILD)
    async def debug_stabilization_db(self, interaction: discord.Interaction):
        """Debug database tables and schema"""
        try:
            import sqlite3
            with sqlite3.connect('stats.db') as conn:
                cursor = conn.cursor()
                
                # Get all tables
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                
                embed = discord.Embed(title="🗃️ Database Debug", color=discord.Color.blue())
                embed.add_field(name="Tables", value="\n".join(tables) or "None", inline=False)
                
                # Check stabilization table
                if 'stabilization' in tables:
                    cursor.execute("SELECT COUNT(*) FROM stabilization")
                    count = cursor.fetchone()[0]
                    embed.add_field(name="Stabilization Records", value=str(count), inline=True)
                
                # Check for health tables
                health_tables = [t for t in tables if 'health' in t.lower() or 'stats' in t.lower() or 'character' in t.lower()]
                embed.add_field(name="Potential Health Tables", value="\n".join(health_tables) or "None found", inline=False)
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Database debug failed: {e}", ephemeral=True)

    @app_commands.command(name="debug_stabilization_tasks", description="Debug stabilization tasks")
    @app_commands.guilds(GUILD)
    async def debug_stabilization_tasks(self, interaction: discord.Interaction):
        """Debug task status"""
        try:
            manager = self.manager
            
            embed = discord.Embed(title="⚡ Task Debug", color=discord.Color.orange())
            
            # Check if tasks object exists
            if hasattr(manager, 'tasks'):
                tasks = manager.tasks
                embed.add_field(name="Tasks Object", value="✅ Exists", inline=True)
                
                # Check task attributes
                has_stab_loop = hasattr(tasks, 'stabilization_loop')
                has_rec_loop = hasattr(tasks, 'recovery_loop')
                
                embed.add_field(name="Stabilization Loop Attr", value="✅" if has_stab_loop else "❌", inline=True)
                embed.add_field(name="Recovery Loop Attr", value="✅" if has_rec_loop else "❌", inline=True)
                
                if has_stab_loop:
                    running = tasks.stabilization_loop.is_running() if hasattr(tasks.stabilization_loop, 'is_running') else False
                    embed.add_field(name="Stabilization Running", value="✅" if running else "❌", inline=True)
                
                if has_rec_loop:
                    running = tasks.recovery_loop.is_running() if hasattr(tasks.recovery_loop, 'is_running') else False
                    embed.add_field(name="Recovery Running", value="✅" if running else "❌", inline=True)
                    
            else:
                embed.add_field(name="Tasks Object", value="❌ Missing", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Task debug failed: {e}", ephemeral=True)

    # Add this to your StabilizationCog class in STABILIZATION_SYSTEM.py

    @app_commands.command(
        name="debug_stabilization_quick", 
        description="Quick stabilization debug check"
    )
    @app_commands.guilds(GUILD)
    async def debug_stabilization_quick(self, interaction: discord.Interaction):
        """Quick debug to see what's broken"""
        try:
            embed = discord.Embed(title="🔍 Quick Debug Check", color=discord.Color.blue())
            
            # Check manager
            embed.add_field(
                name="Manager", 
                value="✅ Exists" if hasattr(self, 'manager') else "❌ Missing", 
                inline=True
            )
            
            # Check processor
            if hasattr(self, 'manager') and hasattr(self.manager, 'processor'):
                embed.add_field(name="Processor", value="✅ Exists", inline=True)
            else:
                embed.add_field(name="Processor", value="❌ Missing", inline=True)
            
            # Check tasks
            if hasattr(self, 'manager') and hasattr(self.manager, 'tasks'):
                tasks = self.manager.tasks
                embed.add_field(name="Tasks Object", value="✅ Exists", inline=True)
                
                # Check if tasks have the loop attributes
                has_stab = hasattr(tasks, 'stabilization_loop')
                has_rec = hasattr(tasks, 'recovery_loop')
                
                embed.add_field(name="Stabilization Loop", value="✅" if has_stab else "❌", inline=True)
                embed.add_field(name="Recovery Loop", value="✅" if has_rec else "❌", inline=True)
                
                # Check if running
                if has_stab:
                    try:
                        running = tasks.stabilization_loop.is_running()
                        embed.add_field(name="Stab Loop Running", value="✅" if running else "❌", inline=True)
                    except Exception as e:
                        embed.add_field(name="Stab Loop Error", value=f"❌ {str(e)[:50]}", inline=True)
                
            else:
                embed.add_field(name="Tasks Object", value="❌ Missing", inline=True)
            
            # Check database
            try:
                if hasattr(self, 'manager') and hasattr(self.manager, 'processor'):
                    # Try a simple database operation
                    test_status = self.manager.processor.database.get_stabilization_status(interaction.user.id)
                    embed.add_field(name="Database", value="✅ Accessible", inline=True)
                else:
                    embed.add_field(name="Database", value="❌ No processor", inline=True)
            except Exception as e:
                embed.add_field(name="Database", value=f"❌ {str(e)[:50]}", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Debug command failed: {e}", ephemeral=True)

async def setup(bot):
    """Required function for Discord.py to load the cog"""
    try:
        await bot.add_cog(StabilizationCog(bot))
        logging.info("✅ Stabilization Cog loaded successfully")
    except Exception as e:
        logging.error(f"❌ Failed to load Stabilization Cog: {e}")
        raise