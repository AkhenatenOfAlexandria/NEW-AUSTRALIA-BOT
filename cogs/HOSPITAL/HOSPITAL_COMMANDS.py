import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID

GUILD = discord.Object(id=GUILD_ID)
TRANSPORT_COST = 1000  # Cost in shekels for hospital transport
HEALING_COST_PER_HP = 1000   # Cost in shekels per HP healed


class HospitalCommands(commands.Cog):
    """Discord slash commands for the hospital system"""
    
    def __init__(self, bot, hospital_core, hospital_treatment):
        self.bot = bot
        self.core = hospital_core
        self.treatment = hospital_treatment
    
    @app_commands.command(name="hospital_status", description="Check your hospital status")
    @app_commands.guilds(GUILD)
    async def hospital_status(self, interaction: discord.Interaction):
        """Check user's hospital status"""
        user_id = interaction.user.id
        
        embed = discord.Embed(
            title="🏥 Hospital Status",
            color=0x3498db
        )
        
        # Check if in hospital
        in_hospital = self.core.is_in_hospital(user_id)
        embed.add_field(
            name="📍 Location",
            value="🏥 In Hospital" if in_hospital else "🌍 Outside Hospital",
            inline=True
        )
        
        # Get health status
        stats_core = self.core.get_stats_core()
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
                current_health = stats['health']
                
                if current_health <= 0:
                    health_status = "💀 Unconscious"
                    health_color = 0xff0000
                elif current_health <= max_health * 0.25:
                    health_status = f"🩸 Critical ({current_health}/{max_health} HP)"
                    health_color = 0xff6b6b
                elif current_health <= max_health * 0.5:
                    health_status = f"🟡 Injured ({current_health}/{max_health} HP)"
                    health_color = 0xffd93d
                else:
                    health_status = f"✅ Healthy ({current_health}/{max_health} HP)"
                    health_color = 0x2ecc71
                
                embed.color = health_color
                embed.add_field(
                    name="🩺 Health Status",
                    value=health_status,
                    inline=True
                )
        
        # Show service costs
        embed.add_field(
            name="💰 Service Costs",
            value=f"🚑 Transport: ₪{TRANSPORT_COST:,} (no tax)\n🏥 Healing: ₪{HEALING_COST_PER_HP:,} per HP (no tax)",
            inline=False
        )
        
        # Information about automatic services
        if in_hospital:
            embed.add_field(
                name="ℹ️ Hospital Services",
                value="• Automatic comprehensive healing when unconscious\n• Heals as much as you can afford\n• Multiple healing sessions per cycle\n• Leave automatically when conscious\n• Cannot be attacked while in hospital\n• No taxes on medical services",
                inline=False
            )
        else:
            embed.add_field(
                name="ℹ️ Emergency Services",
                value="• Automatic transport when unconscious\n• Payment via cash or credit\n• Comprehensive healing until conscious or funds exhausted\n• No taxes on emergency services\n• Tax credits not applicable",
                inline=False
            )
        
        embed.set_footer(text="Hospital provides comprehensive healing until conscious or funds exhausted")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leave_hospital", description="Leave the hospital (if conscious)")
    @app_commands.guilds(GUILD)
    async def leave_hospital(self, interaction: discord.Interaction):
        """Allow conscious players to leave hospital"""
        user_id = interaction.user.id
        
        if not self.core.is_in_hospital(user_id):
            await interaction.response.send_message("❌ You're not in the hospital!", ephemeral=True)
            return
        
        # Check if conscious
        stats_core = self.core.get_stats_core()
        current_health = 0
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                current_health = stats['health']
                if stats['health'] <= 0:
                    await interaction.response.send_message("❌ You cannot leave while unconscious! You need medical treatment first.", ephemeral=True)
                    return
        
        # Discharge patient
        await self.treatment.discharge_patient(user_id, "VOLUNTARY")
        
        embed = discord.Embed(
            title="🚪 Hospital Discharge",
            description=f"**{interaction.user.display_name}** has left the hospital!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="📍 Status",
            value="✅ Successfully discharged",
            inline=True
        )
        
        embed.add_field(
            name="🩺 Health",
            value=f"{current_health} HP",
            inline=True
        )
        
        embed.set_footer(text="Take care of yourself out there!")
        
        await interaction.response.send_message(embed=embed)
        await self.core.send_to_health_log(embed)
    
    @app_commands.command(name="hospital_list", description="Show who is currently in the hospital")
    @app_commands.guilds(GUILD)
    async def hospital_list(self, interaction: discord.Interaction):
        """List all users currently in the hospital"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, transport_time FROM hospital_locations WHERE in_hospital = 1')
            results = cursor.fetchall()
            conn.close()
            
            embed = discord.Embed(
                title="🏥 Hospital Patient List",
                color=0x3498db
            )
            
            if not results:
                embed.description = "✅ No patients currently in the hospital"
                embed.color = 0x2ecc71
            else:
                patients = []
                stats_core = self.core.get_stats_core()
                
                for user_id, transport_time in results:
                    user = self.bot.get_user(user_id)
                    user_name = user.display_name if user else f"Unknown User ({user_id})"
                    
                    # Get health status
                    health_info = ""
                    if stats_core:
                        stats = stats_core.get_user_stats(user_id)
                        if stats:
                            max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
                            current_health = stats['health']
                            
                            if current_health <= 0:
                                health_info = f" - 💀 Unconscious ({current_health}/{max_health} HP)"
                            else:
                                health_info = f" - ✅ Conscious ({current_health}/{max_health} HP)"
                    
                    # Format transport time
                    if transport_time:
                        try:
                            transport_dt = datetime.fromisoformat(transport_time)
                            time_str = transport_dt.strftime("%m/%d %H:%M")
                            patients.append(f"• **{user_name}**{health_info}\n  *Admitted: {time_str}*")
                        except:
                            patients.append(f"• **{user_name}**{health_info}")
                    else:
                        patients.append(f"• **{user_name}**{health_info}")
                
                embed.description = "\n\n".join(patients)
                embed.add_field(
                    name="📊 Statistics",
                    value=f"Total Patients: {len(results)}",
                    inline=True
                )
            
            embed.set_footer(text="Hospital provides comprehensive healing until conscious")
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Failed to get hospital list: {e}")
            await interaction.response.send_message("❌ Failed to retrieve hospital patient list.", ephemeral=True)
    
    @app_commands.command(name="hospital_check", description="Check a specific user's hospital status")
    @app_commands.describe(user="The user to check (leave empty for yourself)")
    @app_commands.guilds(GUILD)
    async def hospital_check(self, interaction: discord.Interaction, user: discord.Member = None):
        """Check hospital status for a specific user"""
        target_user = user if user else interaction.user
        user_id = target_user.id
        
        embed = discord.Embed(
            title=f"🏥 Hospital Status - {target_user.display_name}",
            color=0x3498db
        )
        
        # Check if in hospital
        in_hospital = self.core.is_in_hospital(user_id)
        
        if in_hospital:
            # Get hospital details
            try:
                conn = sqlite3.connect('stats.db')
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT transport_time, last_healing_attempt 
                    FROM hospital_locations 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                conn.close()
                
                transport_time, last_healing = result if result else (None, None)
                
                embed.add_field(
                    name="📍 Location",
                    value="🏥 In Hospital",
                    inline=True
                )
                
                if transport_time:
                    try:
                        transport_dt = datetime.fromisoformat(transport_time)
                        embed.add_field(
                            name="🚑 Admitted",
                            value=transport_dt.strftime("%m/%d/%Y %H:%M"),
                            inline=True
                        )
                    except:
                        pass
                
                if last_healing:
                    try:
                        healing_dt = datetime.fromisoformat(last_healing)
                        embed.add_field(
                            name="🩺 Last Treatment",
                            value=healing_dt.strftime("%m/%d/%Y %H:%M"),
                            inline=True
                        )
                    except:
                        pass
                        
            except Exception as e:
                logging.error(f"❌ Failed to get hospital details: {e}")
                embed.add_field(
                    name="📍 Location",
                    value="🏥 In Hospital",
                    inline=True
                )
        else:
            embed.add_field(
                name="📍 Location",
                value="🌍 Not in Hospital",
                inline=True
            )
        
        # Get health status
        stats_core = self.core.get_stats_core()
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
                current_health = stats['health']
                
                if current_health <= 0:
                    health_status = "💀 Unconscious"
                    health_color = 0xff0000
                    embed.add_field(
                        name="⚠️ Status",
                        value="Requires emergency medical attention",
                        inline=False
                    )
                elif current_health <= max_health * 0.25:
                    health_status = f"🩸 Critical ({current_health}/{max_health} HP)"
                    health_color = 0xff6b6b
                elif current_health <= max_health * 0.5:
                    health_status = f"🟡 Injured ({current_health}/{max_health} HP)"
                    health_color = 0xffd93d
                else:
                    health_status = f"✅ Healthy ({current_health}/{max_health} HP)"
                    health_color = 0x2ecc71
                
                embed.color = health_color
                embed.add_field(
                    name="🩺 Health Status",
                    value=health_status,
                    inline=True
                )
                
                # Check if in combat
                if self.core.is_user_in_combat(user_id):
                    embed.add_field(
                        name="⚔️ Combat Status",
                        value="Currently in combat",
                        inline=True
                    )
        
        # Add relevant information based on status
        if in_hospital and current_health > 0:
            embed.add_field(
                name="ℹ️ Available Actions",
                value="• Use `/leave_hospital` to discharge yourself\n• Hospital monitoring continues while you recover",
                inline=False
            )
        elif not in_hospital and current_health <= 0:
            embed.add_field(
                name="ℹ️ Emergency Status",
                value="• Automatic transport will occur if not in combat\n• Comprehensive healing available once transported",
                inline=False
            )
        
        embed.set_footer(text="Hospital provides comprehensive emergency services")
        await interaction.response.send_message(embed=embed)