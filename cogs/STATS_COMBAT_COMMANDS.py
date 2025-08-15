import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


class StatsCombatCommands(commands.Cog):
    """Combat user commands - /attack and /combat_status"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def get_combat_core(self):
        """Get the combat core cog"""
        return self.bot.get_cog('StatsCombatCore')
    
    def get_combat_manager(self):
        """Get the combat manager cog"""
        return self.bot.get_cog('StatsCombatManager')
    
    def get_combat_reactions(self):
        """Get the combat reactions cog"""
        return self.bot.get_cog('StatsCombatReactions')
    
    @app_commands.command(name="attack", description="Attack another user")
    @app_commands.describe(target="The user to attack")
    @app_commands.guilds(GUILD)
    async def attack(self, interaction: discord.Interaction, target: discord.Member):
        """Attack another user - works for any situation"""
        attacker = interaction.user
        
        # Get required cogs
        combat_core = self.get_combat_core()
        combat_manager = self.get_combat_manager()
        combat_reactions = self.get_combat_reactions()
        
        if not all([combat_core, combat_manager, combat_reactions]):
            await interaction.response.send_message("❌ Combat system not fully available.", ephemeral=True)
            return
        
        # Basic validation
        if target == attacker:
            await interaction.response.send_message("❌ You cannot attack yourself!", ephemeral=True)
            return
        
        if target.bot:
            await interaction.response.send_message("❌ You cannot attack bots!", ephemeral=True)
            return
        
        # Check cooldown
        if combat_manager.is_on_cooldown(attacker.id):
            remaining = combat_manager.get_cooldown_remaining(attacker.id)
            await interaction.response.send_message(f"❌ You're still on cooldown! Wait {remaining:.1f} more seconds.", ephemeral=True)
            return
        
        # Get stats
        stats_core = combat_core.get_stats_core()
        if not stats_core:
            await interaction.response.send_message("❌ Stats system not available.", ephemeral=True)
            return
        
        attacker_stats = stats_core.get_user_stats(attacker.id)
        defender_stats = stats_core.get_user_stats(target.id)
        
        if not attacker_stats:
            await interaction.response.send_message("❌ You don't have character stats yet!", ephemeral=True)
            return
        
        if not defender_stats:
            await interaction.response.send_message("❌ That user doesn't have character stats yet!", ephemeral=True)
            return
        
        # Check if attacker is unconscious
        if attacker_stats['health'] <= 0:
            await interaction.response.send_message("❌ You are unconscious and cannot take actions!", ephemeral=True)
            return
        
        # Check if target is in hospital
        if combat_core.is_user_in_hospital(target.id):
            await interaction.response.send_message("❌ You cannot attack someone who is in the hospital!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Determine if this is a reaction
        is_reaction = False
        if combat_reactions.has_pending_reaction(attacker.id):
            reaction_data = combat_reactions.get_pending_reaction(attacker.id)
            # It's a reaction if they're attacking their attacker
            is_reaction = (reaction_data['attacker_id'] == target.id)
        
        # Execute attack
        await combat_manager.execute_attack(attacker.id, target.id, interaction.channel.id, is_reaction=is_reaction)
    
    @app_commands.command(name="combat_status", description="Check your current combat status")
    @app_commands.guilds(GUILD)
    async def combat_status(self, interaction: discord.Interaction):
        """Check combat status and cooldowns"""
        user_id = interaction.user.id
        
        # Get required cogs
        combat_core = self.get_combat_core()
        combat_manager = self.get_combat_manager()
        combat_reactions = self.get_combat_reactions()
        
        if not all([combat_core, combat_manager, combat_reactions]):
            await interaction.response.send_message("❌ Combat system not fully available.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="⚔️ Combat Status",
            color=0x0099ff,
            timestamp=discord.utils.utcnow()
        )
        
        # Check for pending reactions
        if combat_reactions.has_pending_reaction(user_id):
            reaction_data = combat_reactions.get_pending_reaction(user_id)
            attacker = self.bot.get_user(reaction_data['attacker_id'])
            remaining_time = reaction_data['timeout'] - datetime.now()
            remaining_seconds = max(0, remaining_time.total_seconds())
            
            embed.add_field(
                name="⚡ Pending Reaction",
                value=f"Under attack by **{attacker.display_name if attacker else 'Unknown'}**\n⏰ {remaining_seconds:.1f} seconds to respond",
                inline=False
            )
        else:
            embed.add_field(
                name="🕊️ Status",
                value="No pending reactions",
                inline=False
            )
        
        # Check cooldown
        if combat_manager.is_on_cooldown(user_id):
            remaining = combat_manager.get_cooldown_remaining(user_id)
            embed.add_field(
                name="⏰ Action Cooldown",
                value=f"{remaining:.1f} seconds remaining",
                inline=True
            )
        else:
            embed.add_field(
                name="⏰ Action Cooldown",
                value="Ready to act",
                inline=True
            )
        
        # Show health
        stats_core = combat_core.get_stats_core()
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
                current_health = stats['health']
                
                health_status = "💀 Unconscious" if current_health <= 0 else f"❤️ {current_health}/{max_health} HP"
                embed.add_field(
                    name="🩺 Health",
                    value=health_status,
                    inline=True
                )
        
        embed.add_field(
            name="ℹ️ How It Works",
            value="• Anyone can `/attack` anyone (if not on cooldown)\n• When attacked, you have 6 seconds to respond\n• Use `/retreat` to avoid automatic retaliation",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCombatCommands(bot))
    logging.info("✅ Stats Combat Commands cog loaded successfully")