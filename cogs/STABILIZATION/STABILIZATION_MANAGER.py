import logging
from typing import Optional
import discord
from .STABILIZATION_PROCESSOR import StabilizationProcessor
from .STABILIZATION_LOGGER import StabilizationLogger
from .STABILIZATION_TASKS import StabilizationTasks

class StabilizationManager:
    """Main coordinator for the stabilization system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.processor = StabilizationProcessor()
        self.logger = StabilizationLogger(bot)
        self.tasks = StabilizationTasks(bot, self.processor, self.logger)
        
        logging.info("✅ Stabilization Manager initialized")
    
    def initialize(self):
        """Initialize all stabilization systems"""
        try:
            # Initialize database
            self.processor.database.init_database()
            
            # Start background tasks
            self.tasks.start_tasks()
            
            logging.info("✅ Stabilization system fully initialized")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize stabilization system: {e}")
            raise
    
    def shutdown(self):
        """Shutdown all stabilization systems"""
        try:
            self.tasks.stop_tasks()
            logging.info("⚠️ Stabilization system shut down")
        except Exception as e:
            logging.error(f"Error shutting down stabilization system: {e}")
    
    # Public API methods for other systems to use
    
    def start_stabilization(self, user_id: int) -> bool:
        """Start stabilization for a user (called when they go unconscious)"""
        return self.processor.start_stabilization(user_id)
    
    def add_stabilization_failure(self, user_id: int, count: int = 1) -> str:
        """Add failures when user takes damage while stabilizing"""
        return self.processor.add_stabilization_failure(user_id, count)
    
    def is_user_stabilizing(self, user_id: int) -> bool:
        """Check if user is currently in stabilization"""
        return self.processor.is_user_stabilizing(user_id)
    
    def get_stabilization_status(self, user_id: int):
        """Get stabilization status for a user"""
        return self.processor.get_stabilization_status(user_id)
    
    # Command handlers
    
    async def show_stabilization_status(self, interaction: discord.Interaction, target_user: Optional[discord.Member] = None):
        """Show stabilization status command"""
        try:
            user = target_user or interaction.user
            user_id = user.id
            
            # Get health data
            health_data = self.processor.database.get_user_health(user_id)
            if not health_data:
                await interaction.response.send_message(
                    "❌ No health data found! Character stats may need to be initialized first.", 
                    ephemeral=True
                )
                return
            
            # Get stabilization status
            status = self.processor.get_stabilization_status(user_id)
            
            # Create and send embed
            embed = self.logger.create_status_embed(
                user, 
                health_data['current_health'], 
                health_data['max_health'], 
                status
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logging.error(f"Error in show_stabilization_status: {e}")
            await interaction.response.send_message(
                f"❌ Error checking stabilization status: {e}", 
                ephemeral=True
            )
    
    async def debug_start_stabilization(self, interaction: discord.Interaction, target_user: Optional[discord.Member] = None):
        """Debug command to force start stabilization"""
        try:
            user = target_user or interaction.user
            user_id = user.id
            
            # Get current health
            health_data = self.processor.database.get_user_health(user_id)
            if not health_data:
                await interaction.response.send_message(
                    "❌ No health data found for this user!", 
                    ephemeral=True
                )
                return
            
            current_health = health_data['current_health']
            
            # Set to 0 for testing if not already
            if current_health > 0:
                new_health = self.processor.database.apply_health_change(user_id, -current_health)
                if new_health is None:
                    await interaction.response.send_message("❌ Failed to set health to 0!", ephemeral=True)
                    return
            
            # Start stabilization
            success = self.start_stabilization(user_id)
            
            if success:
                embed = discord.Embed(
                    title="🎲 Debug: Stabilization Started",
                    description=f"Started stabilization process for {user.display_name}",
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Health Set", value="0 HP (for testing)", inline=True)
                embed.add_field(name="Next Roll", value="<t:" + str(int((discord.utils.utcnow().timestamp() + 6))) + ":R>", inline=True)
                embed.set_footer(text="Debug Command")
            else:
                embed = discord.Embed(
                    title="❌ Failed to Start",
                    description="Could not start stabilization process",
                    color=discord.Color.red()
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logging.error(f"Error in debug_start_stabilization: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)
    
    async def debug_damage(self, interaction: discord.Interaction, amount: int, target_user: Optional[discord.Member] = None):
        """Debug command to apply damage"""
        try:
            user = target_user or interaction.user
            user_id = user.id
            
            # Get current health
            health_data = self.processor.database.get_user_health(user_id)
            if not health_data:
                await interaction.response.send_message(
                    "❌ No health data found for this user!", 
                    ephemeral=True
                )
                return
            
            old_health = health_data['current_health']
            new_health = self.processor.database.apply_health_change(user_id, -amount)
            
            if new_health is None:
                await interaction.response.send_message("❌ Failed to apply damage!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="💥 Debug: Damage Applied",
                color=discord.Color.red(),
                timestamp=discord.utils.utcnow()
            )
            
            embed.add_field(name="Player", value=user.display_name, inline=True)
            embed.add_field(name="Damage", value=f"-{amount} HP", inline=True)
            embed.add_field(name="Health", value=f"{old_health} → {new_health}", inline=True)
            
            # Handle stabilization effects
            if new_health <= 0 and old_health > 0:
                # Just went unconscious - start stabilization
                self.start_stabilization(user_id)
                embed.add_field(name="Effect", value="⚠️ Stabilization Started!", inline=False)
            elif new_health <= 0 and old_health <= 0:
                # Already unconscious - add failure
                result = self.add_stabilization_failure(user_id, 1)
                if result == 'death':
                    embed.add_field(name="Effect", value="💀 Death from Stabilization Failures!", inline=False)
                elif result == 'failure_added':
                    embed.add_field(name="Effect", value="💀 Added Stabilization Failure!", inline=False)
            
            embed.set_footer(text="Debug Command")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logging.error(f"Error in debug_damage: {e}")
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)