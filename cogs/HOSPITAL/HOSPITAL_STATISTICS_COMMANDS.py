import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import logging
from datetime import datetime, timedelta

from UTILS.CONFIGURATION import GUILD_ID

GUILD = discord.Object(id=GUILD_ID)
TRANSPORT_COST = 1000  # Cost in shekels for hospital transport
HEALING_COST_PER_HP = 1000   # Cost in shekels per HP healed


class HospitalStatsCommands(commands.Cog):
    """Discord commands for hospital statistics and logging"""
    
    def __init__(self, bot, hospital_core, hospital_treatment):
        self.bot = bot
        self.core = hospital_core
        self.treatment = hospital_treatment
    
    @app_commands.command(name="hospital_stats", description="Show hospital system statistics")
    @app_commands.guilds(GUILD)
    async def hospital_stats(self, interaction: discord.Interaction):
        """Show overall hospital system statistics"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Current patients
            cursor.execute('SELECT COUNT(*) FROM hospital_locations WHERE in_hospital = 1')
            current_patients = cursor.fetchone()[0]
            
            # Total ever transported
            cursor.execute('SELECT COUNT(*) FROM hospital_locations WHERE transport_time IS NOT NULL')
            total_transports = cursor.fetchone()[0]
            
            # Recent action statistics (last 24 hours)
            yesterday = datetime.now() - timedelta(days=1)
            
            cursor.execute('SELECT COUNT(*) FROM hospital_action_log WHERE action_type = "TRANSPORT" AND success = 1 AND timestamp >= ?', (yesterday,))
            recent_transports = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*), SUM(amount), SUM(cost) FROM hospital_action_log WHERE action_type = "HEALING" AND success = 1 AND timestamp >= ?', (yesterday,))
            healing_stats = cursor.fetchone()
            recent_healing_sessions = healing_stats[0] if healing_stats[0] else 0
            recent_hp_healed = healing_stats[1] if healing_stats[1] else 0
            recent_healing_cost = healing_stats[2] if healing_stats[2] else 0
            
            cursor.execute('SELECT COUNT(*) FROM hospital_action_log WHERE action_type LIKE "%DISCHARGE%" AND timestamp >= ?', (yesterday,))
            recent_discharges = cursor.fetchone()[0]
            
            # All-time statistics
            cursor.execute('SELECT COUNT(*), SUM(amount), SUM(cost) FROM hospital_action_log WHERE action_type = "HEALING" AND success = 1')
            all_healing_stats = cursor.fetchone()
            total_healing_sessions = all_healing_stats[0] if all_healing_stats[0] else 0
            total_hp_healed = all_healing_stats[1] if all_healing_stats[1] else 0
            total_healing_cost = all_healing_stats[2] if all_healing_stats[2] else 0
            
            cursor.execute('SELECT COUNT(*) FROM hospital_action_log WHERE action_type = "TRANSPORT" AND success = 1')
            total_successful_transports = cursor.fetchone()[0]
            
            conn.close()
            
            # Get unconscious users not in hospital
            stats_core = self.core.get_stats_core()
            unconscious_outside = 0
            users_in_combat = 0
            
            if stats_core:
                all_users = stats_core.get_all_users_with_stats()
                for user_id in all_users:
                    stats = stats_core.get_user_stats(user_id)
                    if stats and stats['health'] <= 0:
                        if not self.core.is_in_hospital(user_id):
                            unconscious_outside += 1
                            if self.core.is_user_in_combat(user_id):
                                users_in_combat += 1
            
            embed = discord.Embed(
                title="🏥 Hospital System Statistics",
                color=0x3498db
            )
            
            embed.add_field(
                name="📊 Current Status",
                value=f"• Patients in Hospital: **{current_patients}**\n• Unconscious Outside: **{unconscious_outside}**\n• Blocked by Combat: **{users_in_combat}**",
                inline=False
            )
            
            embed.add_field(
                name="📈 Last 24 Hours",
                value=f"• Transports: **{recent_transports}**\n• Healing Sessions: **{recent_healing_sessions}**\n• HP Healed: **{recent_hp_healed:,}**\n• Healing Cost: **₪{recent_healing_cost:,}**\n• Discharges: **{recent_discharges}**",
                inline=True
            )
            
            embed.add_field(
                name="🗂️ All-Time Statistics",
                value=f"• Total Transports: **{total_successful_transports}**\n• Total Healing Sessions: **{total_healing_sessions}**\n• Total HP Healed: **{total_hp_healed:,}**\n• Total Healing Revenue: **₪{total_healing_cost:,}**",
                inline=True
            )
            
            embed.add_field(
                name="💰 Service Costs",
                value=f"• Transport: **₪{TRANSPORT_COST:,}** (no tax)\n• Healing: **₪{HEALING_COST_PER_HP:,}** per HP (no tax)",
                inline=False
            )
            
            embed.add_field(
                name="ℹ️ System Info",
                value="• Automatic checks every 5 minutes\n• Comprehensive healing until conscious\n• Multiple healing sessions per cycle\n• No transport during combat\n• No taxes on medical services",
                inline=False
            )
            
            embed.set_footer(text="Hospital System - Comprehensive emergency medical services")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Failed to get hospital stats: {e}")
            await interaction.response.send_message("❌ Failed to retrieve hospital statistics.", ephemeral=True)
    
    @app_commands.command(name="hospital_log", description="View recent hospital activity")
    @app_commands.describe(user="Filter by specific user (optional)", hours="Hours of history to show (default: 24)")
    @app_commands.guilds(GUILD)
    async def hospital_log(self, interaction: discord.Interaction, user: discord.Member = None, hours: int = 24):
        """View recent hospital activity log"""
        if hours < 1 or hours > 168:  # Max 1 week
            await interaction.response.send_message("❌ Hours must be between 1 and 168 (1 week).", ephemeral=True)
            return
        
        try:
            since_time = datetime.now() - timedelta(hours=hours)
            
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            if user:
                cursor.execute('''
                    SELECT timestamp, username, action_type, amount, cost, payment_method, 
                           success, health_before, health_after, details
                    FROM hospital_action_log 
                    WHERE user_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''', (user.id, since_time))
                title_suffix = f" - {user.display_name}"
            else:
                cursor.execute('''
                    SELECT timestamp, username, action_type, amount, cost, payment_method, 
                           success, health_before, health_after, details
                    FROM hospital_action_log 
                    WHERE timestamp >= ?
                    ORDER BY timestamp DESC
                    LIMIT 20
                ''', (since_time,))
                title_suffix = ""
            
            results = cursor.fetchall()
            conn.close()
            
            embed = discord.Embed(
                title=f"🏥 Hospital Activity Log{title_suffix}",
                description=f"Showing activity from the last {hours} hours",
                color=0x3498db
            )
            
            if not results:
                embed.add_field(
                    name="📭 No Activity",
                    value="No hospital activity found in the specified time period.",
                    inline=False
                )
            else:
                activity_lines = []
                for result in results:
                    timestamp, username, action_type, amount, cost, payment_method, success, health_before, health_after, details = result
                    
                    # Parse timestamp
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%m/%d %H:%M")
                    except:
                        time_str = "Unknown"
                    
                    # Format action based on type
                    if action_type == "TRANSPORT":
                        status = "✅" if success else "❌"
                        activity_lines.append(f"`{time_str}` {status} **{username}** transported (₪{cost}, {payment_method})")
                    
                    elif action_type == "HEALING":
                        status = "✅" if success else "❌"
                        activity_lines.append(f"`{time_str}` {status} **{username}** healed +{amount} HP ({health_before}→{health_after}) (₪{cost}, {payment_method})")
                    
                    elif action_type == "DISCHARGE":
                        activity_lines.append(f"`{time_str}` 🚪 **{username}** discharged ({health_after} HP)")
                    
                    elif action_type == "VOLUNTARY_DISCHARGE":
                        activity_lines.append(f"`{time_str}` 🚪 **{username}** self-discharged ({health_after} HP)")
                    
                    elif action_type == "ADMIN_DISCHARGE":
                        activity_lines.append(f"`{time_str}` 🔧 **{username}** force discharged ({health_after} HP)")
                    
                    else:
                        status = "✅" if success else "❌"
                        activity_lines.append(f"`{time_str}` {status} **{username}** {action_type.lower().replace('_', ' ')}")
                
                # Split into chunks if too long
                activity_text = "\n".join(activity_lines)
                if len(activity_text) > 1024:
                    # Take first entries and add more info
                    activity_text = "\n".join(activity_lines[:15])
                    activity_text += f"\n... and {len(activity_lines) - 15} more entries"
                
                embed.add_field(
                    name="📋 Recent Activity",
                    value=activity_text,
                    inline=False
                )
                
                # Add summary statistics
                successful_actions = sum(1 for r in results if r[6])  # success column
                total_cost = sum(r[4] for r in results if r[6] and r[4])  # cost column for successful actions
                
                embed.add_field(
                    name="📊 Summary",
                    value=f"Total Actions: {len(results)}\nSuccessful: {successful_actions}\nTotal Cost: ₪{total_cost:,}",
                    inline=True
                )
            
            embed.set_footer(text=f"Hospital Activity Log • Showing last {len(results) if results else 0} actions")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Failed to get hospital log: {e}")
            await interaction.response.send_message("❌ Failed to retrieve hospital activity log.", ephemeral=True)
    
    @app_commands.command(name="force_discharge", description="[ADMIN] Force discharge a user from hospital")
    @app_commands.describe(user="The user to discharge from hospital")
    @app_commands.guilds(GUILD)
    async def force_discharge(self, interaction: discord.Interaction, user: discord.Member):
        """Admin command to force discharge a user from hospital"""
        # Check if user has admin permissions (you may want to customize this check)
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need administrator permissions to use this command.", ephemeral=True)
            return
        
        user_id = user.id
        
        if not self.core.is_in_hospital(user_id):
            await interaction.response.send_message(f"❌ {user.display_name} is not in the hospital.", ephemeral=True)
            return
        
        # Get current health for logging
        current_health = 0
        stats_core = self.core.get_stats_core()
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                current_health = stats['health']
        
        # Force discharge
        await self.treatment.discharge_patient(user_id, "ADMIN", interaction.user)
        
        embed = discord.Embed(
            title="🚪 Administrative Discharge",
            description=f"**{user.display_name}** has been forcibly discharged from the hospital by **{interaction.user.display_name}**.",
            color=0xff9500
        )
        
        embed.add_field(
            name="🩺 Patient Health",
            value=f"{current_health} HP",
            inline=True
        )
        
        if current_health <= 0:
            embed.add_field(
                name="⚠️ Warning",
                value="User is still unconscious and vulnerable",
                inline=True
            )
        
        embed.set_footer(text="Administrative action • Use with caution")
        
        await interaction.response.send_message(embed=embed)
        await self.core.send_to_health_log(embed)
        
        # Log the admin action
        logging.info(f"🔧 ADMIN: {interaction.user.display_name} force-discharged {user.display_name} from hospital (Health: {current_health} HP)")


async def setup(bot):
    await bot.add_cog(HospitalStatsCommands(bot))
    logging.info("✅ Hospital Statistics Commands cog loaded successfully")