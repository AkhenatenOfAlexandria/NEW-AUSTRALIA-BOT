import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import logging

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


# Import your economy functions
try:
    from SHEKELS.BALANCE import BALANCE
    from SHEKELS.TRANSFERS import UPDATE_BALANCE  # Use UPDATE_BALANCE instead of WITHDRAW
    from FUNCTIONS import BALANCE_UPDATED
    from UTILS.CONFIGURATION import MONEY_LOG_ID
    ECONOMY_AVAILABLE = True
except ImportError:
    logging.warning("⚠️ Economy modules not found - level buying will be disabled")
    ECONOMY_AVAILABLE = False

class StatsLeveling(commands.Cog):
    """Level system and economy integration for character progression"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def get_stats_core(self):
        """Get the StatsCore cog for accessing core functionality"""
        return self.bot.get_cog('StatsCore')
    
    def is_user_conscious(self, user_id):
        """Check if user is conscious (health > 0)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return True  # Assume conscious if stats unavailable
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return True  # Assume conscious if no stats
        
        return stats['health'] > 0
    
    async def check_consciousness(self, interaction):
        """Check if user is conscious, send error if not"""
        if not self.is_user_conscious(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are unconscious and cannot focus on training or leveling up! "
                "Focus on survival - seek medical attention or wait for stabilization.",
                ephemeral=True
            )
            return False
        return True
    
    def get_level_cost(self, target_level):
        """Get the cost to reach a specific level"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('SELECT cost FROM level_costs WHERE level = ?', (target_level,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logging.error(f"❌ Failed to get level cost: {e}")
            return None
    
    def set_level_cost(self, level, cost):
        """Set the cost for a specific level"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('INSERT OR REPLACE INTO level_costs (level, cost) VALUES (?, ?)', (level, cost))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"❌ Failed to set level cost: {e}")
            return False
    
    def update_user_level(self, user_id, new_level):
        """Update a user's level and recalculate health"""
        try:
            stats_core = self.get_stats_core()
            if not stats_core:
                return False
            
            stats = stats_core.get_user_stats(user_id)
            if not stats:
                return False
            
            new_health = stats_core.calculate_health(stats['constitution'], new_level)
            
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_stats 
                SET level = ?, health = ? 
                WHERE user_id = ?
            ''', (new_level, new_health, user_id))
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to update user level: {e}")
            return False
    
    @app_commands.command(name="level_up", description="Buy the next level with Shekels")
    @app_commands.guilds(GUILD)
    async def level_up(self, interaction: discord.Interaction):
        """Buy the next level using Shekels"""
        if not ECONOMY_AVAILABLE:
            await interaction.response.send_message("❌ Economy system not available.", ephemeral=True)
            return
        
        # Check consciousness
        if not await self.check_consciousness(interaction):
            return
        
        await interaction.response.defer()
        
        try:
            stats_core = self.get_stats_core()
            if not stats_core:
                await interaction.followup.send("❌ Stats core system not available.")
                return
            
            stats = stats_core.get_user_stats(interaction.user.id)
            if not stats:
                await interaction.followup.send("❌ You don't have character stats yet! An admin can assign them using `/assign_stats`.")
                return
            
            current_level = stats.get('level', 1)
            next_level = current_level + 1
            
            if next_level > 20:
                await interaction.followup.send("❌ You're already at the maximum level (20)!")
                return
            
            cost = self.get_level_cost(next_level)
            if cost is None:
                await interaction.followup.send(f"❌ No cost set for level {next_level}. Contact an administrator.")
                return
            
            balance = BALANCE(interaction.user)
            cash = balance[0]
            
            if cash < cost:
                await interaction.followup.send(f"❌ You need ₪{cost:,} to reach level {next_level}, but you only have ₪{cash:,} cash!")
                return
            
            try:
                # Remove money from cash instead of using WITHDRAW
                UPDATE_BALANCE(interaction.user, -cost, "CASH")
                
                if self.update_user_level(interaction.user.id, next_level):
                    new_stats = stats_core.get_user_stats(interaction.user.id)
                    
                    embed = discord.Embed(
                        title="🌟 Level Up!",
                        description=f"Congratulations! You've reached **Level {next_level}**!",
                        color=0xffd700
                    )
                    embed.add_field(name="💰 Cost", value=f"₪{cost:,}", inline=True)
                    embed.add_field(name="❤️ New Health", value=f"{new_stats['health']} HP", inline=True)
                    embed.add_field(name="💵 Remaining Cash", value=f"₪{cash - cost:,}", inline=True)
                    embed.set_thumbnail(url=interaction.user.display_avatar.url)
                    
                    await interaction.followup.send(embed=embed)
                    
                    try:
                        money_log = self.bot.get_channel(MONEY_LOG_ID)
                        if money_log:
                            log_embed = BALANCE_UPDATED(
                                TIME=interaction.created_at,
                                USER=interaction.user,
                                REASON="LEVEL_UP",
                                CASH=-cost,  # This is now correct - cash decreased by cost
                                MESSAGE=None
                            )
                            await money_log.send(embed=log_embed)
                    except Exception as e:
                        logging.error(f"Failed to log level up transaction: {e}")
                    
                else:
                    # If level update failed, refund the money
                    UPDATE_BALANCE(interaction.user, cost, "CASH")
                    await interaction.followup.send("❌ Failed to update your level. Money has been refunded.")
                    
            except Exception as e:
                await interaction.followup.send(f"❌ Transaction failed: {str(e)}")
            
        except Exception as e:
            logging.error(f"❌ Error in level_up command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="level_costs", description="View the costs for each level")
    @app_commands.guilds(GUILD)
    async def level_costs(self, interaction: discord.Interaction):
        """Display the cost chart for all levels - allowed while unconscious"""
        await interaction.response.defer()
        
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('SELECT level, cost FROM level_costs ORDER BY level')
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                await interaction.followup.send("❌ No level costs found in the database.")
                return
            
            embed = discord.Embed(
                title="💰 Level Costs",
                description="Cost in Shekels to reach each level:",
                color=0x00ff00
            )
            
            levels_1_10 = []
            levels_11_20 = []
            
            for level, cost in results:
                cost_str = f"Level {level}: ₪{cost:,}"
                if level <= 10:
                    levels_1_10.append(cost_str)
                else:
                    levels_11_20.append(cost_str)
            
            if levels_1_10:
                embed.add_field(
                    name="🌟 Levels 2-10", 
                    value="\n".join(levels_1_10), 
                    inline=True
                )
            
            if levels_11_20:
                embed.add_field(
                    name="⭐ Levels 11-20", 
                    value="\n".join(levels_11_20), 
                    inline=True
                )
            
            stats_core = self.get_stats_core()
            if stats_core:
                stats = stats_core.get_user_stats(interaction.user.id)
                if stats:
                    current_level = stats.get('level', 1)
                    next_level = current_level + 1
                    next_cost = self.get_level_cost(next_level)
                    
                    status_text = f"Your Level: **{current_level}**"
                    if next_cost and next_level <= 20:
                        status_text += f"\nNext Level Cost: **₪{next_cost:,}**"
                    elif next_level > 20:
                        status_text += f"\n**Maximum Level Reached!**"
                    
                    # Add consciousness warning if unconscious
                    if not self.is_user_conscious(interaction.user.id):
                        status_text += f"\n⚠️ **Unconscious** - Cannot level up!"
                    
                    embed.add_field(name="📊 Your Status", value=status_text, inline=False)
            
            embed.set_footer(text="Use /level_up to purchase your next level!")
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Error in level_costs command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="set_level_cost", description="[ADMIN] Set the cost for a specific level")
    @app_commands.describe(level="Level to set cost for (2-20)", cost="Cost in Shekels")
    @app_commands.guilds(GUILD)
    async def set_level_cost_command(self, interaction: discord.Interaction, level: int, cost: int):
        """Admin command to set level costs - admins can use while unconscious"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        if level < 2 or level > 20:
            await interaction.response.send_message("❌ Level must be between 2 and 20.", ephemeral=True)
            return
        
        if cost < 0:
            await interaction.response.send_message("❌ Cost cannot be negative.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            if self.set_level_cost(level, cost):
                embed = discord.Embed(
                    title="✅ Level Cost Updated",
                    description=f"Level {level} now costs **₪{cost:,}**",
                    color=0x00ff00
                )
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Failed to update level cost.")
                
        except Exception as e:
            logging.error(f"❌ Error in set_level_cost command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="set_user_level", description="[ADMIN] Set a user's level directly")
    @app_commands.describe(member="User to set level for", level="New level (1-20)")
    @app_commands.guilds(GUILD)
    async def set_user_level_command(self, interaction: discord.Interaction, member: discord.Member, level: int):
        """Admin command to set a user's level directly - admins can use while unconscious"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        if level < 1 or level > 20:
            await interaction.response.send_message("❌ Level must be between 1 and 20.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            stats_core = self.get_stats_core()
            if not stats_core:
                await interaction.followup.send("❌ Stats core system not available.")
                return
            
            stats = stats_core.get_user_stats(member.id)
            if not stats:
                await interaction.followup.send(f"❌ {member.display_name} doesn't have character stats yet!")
                return
            
            if self.update_user_level(member.id, level):
                new_stats = stats_core.get_user_stats(member.id)
                
                embed = discord.Embed(
                    title="✅ Level Set",
                    description=f"{member.display_name} is now **Level {level}**!",
                    color=0x00ff00
                )
                embed.add_field(name="❤️ New Health", value=f"{new_stats['health']} HP", inline=True)
                embed.set_thumbnail(url=member.display_avatar.url)
                
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Failed to update user's level.")
                
        except Exception as e:
            logging.error(f"❌ Error in set_user_level command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(StatsLeveling(bot))
    logging.info("✅ Stats Leveling cog loaded successfully")