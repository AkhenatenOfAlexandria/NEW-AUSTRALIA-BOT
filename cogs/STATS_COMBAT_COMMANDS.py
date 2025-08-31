import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)

# Set up logger for this module
logger = logging.getLogger(__name__)

class StatsCombatCommands(commands.Cog):
    """Combat user commands - /attack and /combat_status"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("StatsCombatCommands initialized")
    
    def get_combat_core(self):
        """Get the combat core cog"""
        cog = self.bot.get_cog('StatsCombatCore')
        logger.debug(f"Combat core cog: {'Found' if cog else 'NOT FOUND'}")
        return cog
    
    def get_combat_manager(self):
        """Get the combat manager cog"""
        cog = self.bot.get_cog('StatsCombatManager')
        logger.debug(f"Combat manager cog: {'Found' if cog else 'NOT FOUND'}")
        return cog
    
    def get_combat_reactions(self):
        """Get the combat reactions cog"""
        cog = self.bot.get_cog('StatsCombatReactions')
        logger.debug(f"Combat reactions cog: {'Found' if cog else 'NOT FOUND'}")
        return cog
    
    @app_commands.command(name="attack", description="Attack another user")
    @app_commands.describe(target="The user to attack")
    @app_commands.guilds(GUILD)
    async def attack(self, interaction: discord.Interaction, target: discord.Member):
        """Attack another user - works for any situation"""
        attacker = interaction.user
        logger.info(f"Attack command initiated: {attacker.display_name} ({attacker.id}) -> {target.display_name} ({target.id})")
        
        try:
            # Get required cogs
            logger.debug("Getting required cogs...")
            combat_core = self.get_combat_core()
            combat_manager = self.get_combat_manager()
            combat_reactions = self.get_combat_reactions()
            
            if not all([combat_core, combat_manager, combat_reactions]):
                missing_cogs = []
                if not combat_core: missing_cogs.append("StatsCombatCore")
                if not combat_manager: missing_cogs.append("StatsCombatManager")
                if not combat_reactions: missing_cogs.append("StatsCombatReactions")
                logger.error(f"Missing required cogs: {', '.join(missing_cogs)}")
                await interaction.response.send_message("⛔ Combat system not fully available.", ephemeral=True)
                return
            
            logger.debug("All required cogs found")
            
            # Basic validation
            logger.debug("Performing basic validation...")
            if target == attacker:
                logger.info(f"User {attacker.id} tried to attack themselves")
                await interaction.response.send_message("⛔ You cannot attack yourself!", ephemeral=True)
                return
            
            if target.bot:
                logger.info(f"User {attacker.id} tried to attack bot {target.id}")
                await interaction.response.send_message("⛔ You cannot attack bots!", ephemeral=True)
                return
            
            logger.debug("Basic validation passed")
            
            # Check cooldown
            logger.debug("Checking cooldown...")
            if combat_manager.is_on_cooldown(attacker.id):
                remaining = combat_manager.get_cooldown_remaining(attacker.id)
                logger.info(f"User {attacker.id} on cooldown: {remaining:.1f}s remaining")
                await interaction.response.send_message(f"⛔ You're still on cooldown! Wait {remaining:.1f} more seconds.", ephemeral=True)
                return
            
            logger.debug("Cooldown check passed")
            
            # Get stats
            logger.debug("Getting stats core...")
            stats_core = combat_core.get_stats_core()
            if not stats_core:
                logger.error("Stats core not available from combat core")
                await interaction.response.send_message("⛔ Stats system not available.", ephemeral=True)
                return
            
            logger.debug("Getting user stats...")
            attacker_stats = stats_core.get_user_stats(attacker.id)
            defender_stats = stats_core.get_user_stats(target.id)
            
            logger.debug(f"Attacker stats: {'Found' if attacker_stats else 'NOT FOUND'}")
            logger.debug(f"Defender stats: {'Found' if defender_stats else 'NOT FOUND'}")
            
            if not attacker_stats:
                logger.info(f"Attacker {attacker.id} has no stats")
                await interaction.response.send_message("⛔ You don't have stats yet!", ephemeral=True)
                return
            
            if not defender_stats:
                logger.info(f"Defender {target.id} has no stats")
                await interaction.response.send_message("⛔ That user doesn't have stats yet!", ephemeral=True)
                return
            
            logger.debug("Stats validation passed")
            
            # Check if attacker is unconscious
            logger.debug(f"Checking attacker health: {attacker_stats['health']}")
            if attacker_stats['health'] <= 0:
                logger.info(f"Attacker {attacker.id} is unconscious (health: {attacker_stats['health']})")
                await interaction.response.send_message("⛔ You are unconscious and cannot take actions!", ephemeral=True)
                return
            
            # Check if target is in hospital
            logger.debug("Checking if target is in hospital...")
            if combat_core.is_user_in_hospital(target.id):
                logger.info(f"Target {target.id} is in hospital")
                await interaction.response.send_message("⛔ You cannot attack someone who is in the hospital!", ephemeral=True)
                return
            
            logger.debug("Hospital check passed")
            
            logger.debug("Deferring interaction response...")
            await interaction.response.defer()
            
            # Determine if this is a reaction
            logger.debug("Checking for pending reactions...")
            is_reaction = False
            if combat_reactions.has_pending_reaction(attacker.id):
                reaction_data = combat_reactions.get_pending_reaction(attacker.id)
                # It's a reaction if they're attacking their attacker
                is_reaction = (reaction_data['attacker_id'] == target.id)
                logger.debug(f"Pending reaction found. Is reaction attack: {is_reaction}")
            else:
                logger.debug("No pending reaction")
            
            # Execute attack
            logger.info(f"Executing attack: attacker={attacker.id}, target={target.id}, channel={interaction.channel.id}, is_reaction={is_reaction}")
            await combat_manager.execute_attack(attacker.id, target.id, interaction.channel.id, is_reaction=is_reaction)
            logger.info("Attack execution completed successfully")
            
        except Exception as e:
            logger.error(f"Unexpected error in attack command: {type(e).__name__}: {str(e)}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("⛔ An error occurred while processing the attack.", ephemeral=True)
                else:
                    await interaction.followup.send("⛔ An error occurred while processing the attack.", ephemeral=True)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {followup_error}")
    
    @app_commands.command(name="combat_status", description="Check your current combat status")
    @app_commands.guilds(GUILD)
    async def combat_status(self, interaction: discord.Interaction):
        """Check combat status and cooldowns"""
        user_id = interaction.user.id
        logger.info(f"Combat status command initiated by user {user_id}")
        
        try:
            # Get required cogs
            logger.debug("Getting required cogs for combat status...")
            combat_core = self.get_combat_core()
            combat_manager = self.get_combat_manager()
            combat_reactions = self.get_combat_reactions()
            
            if not all([combat_core, combat_manager, combat_reactions]):
                missing_cogs = []
                if not combat_core: missing_cogs.append("StatsCombatCore")
                if not combat_manager: missing_cogs.append("StatsCombatManager")
                if not combat_reactions: missing_cogs.append("StatsCombatReactions")
                logger.error(f"Missing required cogs for combat status: {', '.join(missing_cogs)}")
                await interaction.response.send_message("⛔ Combat system not fully available.", ephemeral=True)
                return
            
            logger.debug("Creating combat status embed...")
            embed = discord.Embed(
                title="⚔️ Combat Status",
                color=0x0099ff,
                timestamp=discord.utils.utcnow()
            )
            
            # Check for pending reactions
            logger.debug("Checking for pending reactions...")
            if combat_reactions.has_pending_reaction(user_id):
                reaction_data = combat_reactions.get_pending_reaction(user_id)
                attacker = self.bot.get_user(reaction_data['attacker_id'])
                remaining_time = reaction_data['timeout'] - datetime.now()
                remaining_seconds = max(0, remaining_time.total_seconds())
                
                logger.debug(f"Pending reaction found: attacker={reaction_data['attacker_id']}, remaining={remaining_seconds:.1f}s")
                embed.add_field(
                    name="⚡ Pending Reaction",
                    value=f"Under attack by **{attacker.display_name if attacker else 'Unknown'}**\n⏰ {remaining_seconds:.1f} seconds to respond",
                    inline=False
                )
            else:
                logger.debug("No pending reactions")
                embed.add_field(
                    name="🕊️ Status",
                    value="No pending reactions",
                    inline=False
                )
            
            # Check cooldown
            logger.debug("Checking cooldown status...")
            if combat_manager.is_on_cooldown(user_id):
                remaining = combat_manager.get_cooldown_remaining(user_id)
                logger.debug(f"User on cooldown: {remaining:.1f}s remaining")
                embed.add_field(
                    name="⏰ Action Cooldown",
                    value=f"{remaining:.1f} seconds remaining",
                    inline=True
                )
            else:
                logger.debug("User not on cooldown")
                embed.add_field(
                    name="⏰ Action Cooldown",
                    value="Ready to act",
                    inline=True
                )
            
            # Show health
            logger.debug("Getting health information...")
            stats_core = combat_core.get_stats_core()
            if stats_core:
                stats = stats_core.get_user_stats(user_id)
                if stats:
                    max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
                    current_health = stats['health']
                    
                    health_status = "❤️ {current_health}/{max_health} HP"
                    logger.debug(f"Health status: {health_status}")
                    embed.add_field(
                        name="🩺 Health",
                        value=health_status,
                        inline=True
                    )
                else:
                    logger.debug("No stats found for user")
            else:
                logger.debug("Stats core not available")
            
            embed.add_field(
                name="ℹ️ How It Works",
                value="• Anyone can `/attack` anyone (if not on cooldown)\n• When attacked, you have 6 seconds to respond\n• Use `/retreat` to avoid automatic retaliation",
                inline=False
            )
            
            logger.debug("Sending combat status embed...")
            await interaction.response.send_message(embed=embed)
            logger.info("Combat status command completed successfully")
            
        except Exception as e:
            logger.error(f"Unexpected error in combat_status command: {type(e).__name__}: {str(e)}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("⛔ An error occurred while getting combat status.", ephemeral=True)
                else:
                    await interaction.followup.send("⛔ An error occurred while getting combat status.", ephemeral=True)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {followup_error}")

async def setup(bot):
    try:
        await bot.add_cog(StatsCombatCommands(bot))
        logger.info("✅ Stats Combat Commands cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Stats Combat Commands cog: {type(e).__name__}: {str(e)}", exc_info=True)
        raise