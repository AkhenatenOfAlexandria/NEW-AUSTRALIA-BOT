import discord
from discord.ext import commands
from discord import app_commands
import logging

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)

class StatsAdmin(commands.Cog):
    """Admin commands for managing user stats"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def get_stats_core(self):
        """Get the StatsCore cog for accessing core functionality"""
        return self.bot.get_cog('StatsCore')
    
    @app_commands.command(name="assign_stats", description="[ADMIN] Assign stats to a specific user")
    @app_commands.describe(member="The member to assign stats to")
    @app_commands.guilds(GUILD)
    async def assign_stats(self, interaction: discord.Interaction, member: discord.Member):
        """Admin command to assign stats to a specific user"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            stats_core = self.get_stats_core()
            if not stats_core:
                await interaction.followup.send("❌ Stats core system not available.")
                return
            
            stats = stats_core.generate_stats()
            
            if stats_core.save_user_stats(member.id, member.display_name, stats):
                embed = stats_core.create_stats_embed(member, stats)
                embed.title = f"✅ Stats assigned to {member.display_name}"
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Failed to save stats to database.")
                
        except Exception as e:
            logging.error(f"❌ Error in assign_stats command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="assign_all_stats", description="[ADMIN] Assign stats to all members who don't have them")
    @app_commands.guilds(GUILD)
    async def assign_all_stats(self, interaction: discord.Interaction):
        """Admin command to assign stats to all members without stats"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            stats_core = self.get_stats_core()
            if not stats_core:
                await interaction.followup.send("❌ Stats core system not available.")
                return
            
            guild = interaction.guild
            users_with_stats = set(stats_core.get_all_users_with_stats())
            
            assigned_count = 0
            failed_count = 0
            
            members_to_assign = [
                member for member in guild.members 
                if not member.bot and member.id not in users_with_stats
            ]
            
            if not members_to_assign:
                await interaction.followup.send("✅ All non-bot members already have stats assigned!")
                return
            
            total_members = len(members_to_assign)
            progress_embed = discord.Embed(
                title="📊 Assigning Stats",
                description=f"Assigning stats to {total_members} members...",
                color=0xffff00
            )
            await interaction.followup.send(embed=progress_embed)
            
            for i, member in enumerate(members_to_assign):
                try:
                    stats = stats_core.generate_stats()
                    if stats_core.save_user_stats(member.id, member.display_name, stats):
                        assigned_count += 1
                        logging.info(f"✅ Assigned stats to {member.display_name} ({i+1}/{total_members})")
                    else:
                        failed_count += 1
                        logging.error(f"❌ Failed to assign stats to {member.display_name}")
                        
                except Exception as e:
                    failed_count += 1
                    logging.error(f"❌ Error assigning stats to {member.display_name}: {e}")
            
            completion_embed = discord.Embed(
                title="📊 Stats Assignment Complete",
                color=0x00ff00 if failed_count == 0 else 0xff9900
            )
            completion_embed.add_field(name="✅ Successfully Assigned", value=str(assigned_count), inline=True)
            completion_embed.add_field(name="❌ Failed", value=str(failed_count), inline=True)
            completion_embed.add_field(name="📈 Total Processed", value=str(total_members), inline=True)
            
            await interaction.edit_original_response(embed=completion_embed)
            
        except Exception as e:
            logging.error(f"❌ Error in assign_all_stats command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="reroll_stats", description="[ADMIN] Reroll stats for a specific user")
    @app_commands.describe(member="The member whose stats to reroll")
    @app_commands.guilds(GUILD)
    async def reroll_stats(self, interaction: discord.Interaction, member: discord.Member):
        """Admin command to reroll stats for a user"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            stats_core = self.get_stats_core()
            if not stats_core:
                await interaction.followup.send("❌ Stats core system not available.")
                return
            
            stats = stats_core.generate_stats()
            
            if stats_core.save_user_stats(member.id, member.display_name, stats):
                embed = stats_core.create_stats_embed(member, stats)
                embed.title = f"🎲 Stats rerolled for {member.display_name}"
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send("❌ Failed to save new stats to database.")
                
        except Exception as e:
            logging.error(f"❌ Error in reroll_stats command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(StatsAdmin(bot))
    logging.info("✅ Stats Admin cog loaded successfully")