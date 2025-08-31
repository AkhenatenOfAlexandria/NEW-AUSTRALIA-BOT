import discord
from discord.ext import commands
from discord import app_commands
import logging
import random
from datetime import datetime
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID, MONEY_LOG_ID
from UTILS.FUNCTIONS import BALANCE_UPDATED
from SHEKELS.BALANCE import BALANCE
from SHEKELS.TRANSFERS import UPDATE_BALANCE, PAY

GUILD = discord.Object(id=GUILD_ID)

# Set up logger for this module
logger = logging.getLogger(__name__)

class StatsLootCommands(commands.Cog):
    """Loot system - steal cash from other players with stealth mechanics"""
    
    def __init__(self, bot):
        self.bot = bot
        logger.info("StatsLootCommands initialized")
    
    def get_stats_core(self):
        """Get the stats core cog"""
        cog = self.bot.get_cog('StatsCore')
        logger.debug(f"Stats core cog: {'Found' if cog else 'NOT FOUND'}")
        return cog
    
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
    
    def get_ability_modifier(self, ability_score):
        """Calculate D&D ability modifier from ability score"""
        return (ability_score - 10) // 2
    
    def calculate_passive_perception(self, stats):
        """Calculate passive perception (10 + wisdom modifier + proficiency if applicable)"""
        wisdom_modifier = self.get_ability_modifier(stats['wisdom'])
        level = stats.get('level', 1)
        '''proficiency_bonus = 2 + ((level - 1) // 4)  # D&D proficiency progression
        
        # Assume proficiency in Perception for characters level 3+
        perception_prof = proficiency_bonus if level >= 3 else 0'''
        
        return 10 + wisdom_modifier
    
    def make_stealth_check(self, looter_stats, target_stats):
        """Make a stealth check vs passive perception"""
        # Looter's stealth roll (1d20 + dex modifier + proficiency)
        roll = random.randint(1, 20)
        dex_modifier = self.get_ability_modifier(looter_stats['dexterity'])
        level = looter_stats.get('level', 1)
        '''proficiency_bonus = 2 + ((level - 1) // 4)
        
        # Assume proficiency in Stealth for characters level 2+
        stealth_prof = proficiency_bonus if level >= 2 else 0'''
        
        stealth_total = roll + dex_modifier
        
        # Target's passive perception
        passive_perception = self.calculate_passive_perception(target_stats)
        
        # Natural 20 always succeeds, natural 1 always fails
        if roll == 20:
            success = True
        elif roll == 1:
            success = False
        else:
            success = stealth_total >= passive_perception
        
        return {
            'roll': roll,
            'dex_modifier': dex_modifier,
            # 'proficiency': stealth_prof,
            'total': stealth_total,
            'passive_perception': passive_perception,
            'success': success,
            'natural_20': roll == 20,
            'natural_1': roll == 1
        }
    
    def create_loot_success_embed(self, looter, target, stealth_result, amount_stolen, tax_amount, net_received):
        """Create embed for successful loot attempt"""
        embed = discord.Embed(
            title="💰 Successful Pickpocket",
            description=f"**{looter.display_name}** successfully pickpockets **{target.display_name}**!",
            color=0x00ff00,
            timestamp=discord.utils.utcnow()
        )
        
        # Stealth details
        if stealth_result['natural_20']:
            stealth_desc = f"🎯 **CRITICAL SUCCESS!** Natural 20!"
        else:
            stealth_desc = f"✅ **Success!** ({stealth_result['roll']} + {stealth_result['dex_modifier']} = {stealth_result['total']} vs {stealth_result['passive_perception']})"
        
        embed.add_field(name="🎲 Stealth Check", value=stealth_desc, inline=False)
        
        # Money stolen
        embed.add_field(name="💵 Amount Stolen", value=f"₪{amount_stolen:,}", inline=True)
        embed.add_field(name="🏛️ Tax Paid", value=f"₪{tax_amount:,}", inline=True)
        embed.add_field(name="💰 Net Received", value=f"₪{net_received:,}", inline=True)
        
        embed.add_field(
            name="🕵️ Stealth Success",
            value=f"The victim remains unaware of the theft!",
            inline=False
        )
        
        embed.set_footer(text="Crime pays... sometimes")
        
        return embed
    
    def create_loot_failure_embed(self, looter, target, stealth_result):
        """Create embed for failed loot attempt"""
        embed = discord.Embed(
            title="🚨 Pickpocket Attempt Failed",
            description=f"**{looter.display_name}** was caught trying to pickpocket **{target.display_name}**!",
            color=0xff0000,
            timestamp=discord.utils.utcnow()
        )
        
        # Stealth details
        if stealth_result['natural_1']:
            stealth_desc = f"💥 **CRITICAL FAILURE!** Natural 1!"
        else:
            stealth_desc = f"❌ **Failure!** ({stealth_result['roll']} + {stealth_result['dex_modifier']} = {stealth_result['total']} vs {stealth_result['passive_perception']})"
        
        embed.add_field(name="🎲 Stealth Check", value=stealth_desc, inline=False)
        
        embed.add_field(
            name="⚡ Combat Initiated",
            value=f"**{target.display_name}** notices the theft attempt and can retaliate!",
            inline=False
        )
        
        embed.set_footer(text="Sometimes crime doesn't pay")
        
        return embed
    
    @app_commands.command(name="loot", description="Attempt to steal cash from another player")
    @app_commands.describe(target="The user to attempt to pickpocket")
    @app_commands.guilds(GUILD)
    async def loot(self, interaction: discord.Interaction, target: discord.Member):
        """Attempt to loot another player's cash"""
        looter = interaction.user
        logger.info(f"Loot command initiated: {looter.display_name} ({looter.id}) -> {target.display_name} ({target.id})")
        
        try:
            # Get required cogs
            logger.debug("Getting required cogs...")
            stats_core = self.get_stats_core()
            combat_core = self.get_combat_core()
            combat_manager = self.get_combat_manager()
            combat_reactions = self.get_combat_reactions()
            
            if not stats_core:
                logger.error("Stats core not available")
                await interaction.response.send_message("⛔ Stats system not available.", ephemeral=True)
                return
            
            if not all([combat_core, combat_manager, combat_reactions]):
                missing_cogs = []
                if not combat_core: missing_cogs.append("StatsCombatCore")
                if not combat_manager: missing_cogs.append("StatsCombatManager")
                if not combat_reactions: missing_cogs.append("StatsCombatReactions")
                logger.error(f"Missing required combat cogs: {', '.join(missing_cogs)}")
                await interaction.response.send_message("⛔ Combat system not fully available.", ephemeral=True)
                return
            
            logger.debug("All required cogs found")
            
            # Basic validation
            logger.debug("Performing basic validation...")
            if target == looter:
                logger.info(f"User {looter.id} tried to loot themselves")
                await interaction.response.send_message("⛔ You cannot pickpocket yourself!", ephemeral=True)
                return
            
            if target.bot:
                logger.info(f"User {looter.id} tried to loot bot {target.id}")
                await interaction.response.send_message("⛔ You cannot pickpocket bots!", ephemeral=True)
                return
            
            logger.debug("Basic validation passed")
            
            # Check cooldown
            logger.debug("Checking cooldown...")
            if combat_manager.is_on_cooldown(looter.id):
                remaining = combat_manager.get_cooldown_remaining(looter.id)
                logger.info(f"User {looter.id} on cooldown: {remaining:.1f}s remaining")
                await interaction.response.send_message(f"⛔ You're still on cooldown! Wait {remaining:.1f} more seconds.", ephemeral=True)
                return
            
            logger.debug("Cooldown check passed")
            
            # Get stats
            logger.debug("Getting user stats...")
            looter_stats = stats_core.get_user_stats(looter.id)
            target_stats = stats_core.get_user_stats(target.id)
            
            logger.debug(f"Looter stats: {'Found' if looter_stats else 'NOT FOUND'}")
            logger.debug(f"Target stats: {'Found' if target_stats else 'NOT FOUND'}")
            
            if not looter_stats:
                logger.info(f"Looter {looter.id} has no stats")
                await interaction.response.send_message("⛔ You don't have stats yet!", ephemeral=True)
                return
            
            if not target_stats:
                logger.info(f"Target {target.id} has no stats")
                await interaction.response.send_message("⛔ That user doesn't have stats yet!", ephemeral=True)
                return
            
            logger.debug("Stats validation passed")
            
            # Check if looter is unconscious
            logger.debug(f"Checking looter health: {looter_stats['health']}")
            if looter_stats['health'] <= 0:
                logger.info(f"Looter {looter.id} is unconscious (health: {looter_stats['health']})")
                await interaction.response.send_message("⛔ You are unconscious and cannot take actions!", ephemeral=True)
                return
            
            # Check if target is in hospital
            logger.debug("Checking if target is in hospital...")
            if combat_core.is_user_in_hospital(target.id):
                logger.info(f"Target {target.id} is in hospital")
                await interaction.response.send_message("⛔ You cannot pickpocket someone who is in the hospital!", ephemeral=True)
                return
            
            logger.debug("Hospital check passed")
            
            # Check target's cash
            logger.debug("Checking target's cash...")
            target_balance = BALANCE(target)
            target_cash = target_balance[0]
            
            if target_cash <= 0:
                logger.info(f"Target {target.id} has no cash to steal ({target_cash})")
                await interaction.response.send_message("⛔ That user has no cash to steal!", ephemeral=True)
                return
            
            logger.debug(f"Target has ₪{target_cash:,} cash available")
            
            logger.debug("Deferring interaction response...")
            await interaction.response.defer()
            
            # Make stealth check
            logger.debug("Making stealth check...")
            stealth_result = self.make_stealth_check(looter_stats, target_stats)
            logger.debug(f"Stealth check result: {stealth_result}")
            
            # Set cooldown regardless of success/failure
            combat_manager.set_cooldown(looter.id)
            
            if stealth_result['success']:
                # Successful theft
                logger.info(f"Successful loot: {looter.id} stole from {target.id}")
                
                try:
                    # Use PAY function to transfer all cash (with tax)
                    # This handles the tax calculation and treasury updates
                    pay_result = PAY(target, looter, target_cash)
                    pay_message = pay_result[0]
                    actual_tax = pay_result[1]
                    net_received = target_cash - actual_tax
                    
                    # Create success embed
                    embed = self.create_loot_success_embed(
                        looter, target, stealth_result, 
                        target_cash, actual_tax, net_received
                    )
                    
                    await interaction.followup.send(embed=embed)
                    
                    # Log to money log
                    money_log = self.bot.get_channel(MONEY_LOG_ID)
                    if money_log:
                        # Log the theft from target's perspective
                        log_embed = BALANCE_UPDATED(
                            TIME=interaction.created_at,
                            USER=target,
                            REASON="PICKPOCKETED",
                            CASH=-target_cash,
                            MESSAGE=None
                        )
                        log_embed.add_field(
                            name="🕵️ Stolen By",
                            value=f"{looter.display_name}",
                            inline=True
                        )
                        await money_log.send(embed=log_embed)
                        
                        # Log the gain from looter's perspective
                        log_embed = BALANCE_UPDATED(
                            TIME=interaction.created_at,
                            USER=looter,
                            REASON="SUCCESSFUL_LOOT",
                            CASH=net_received,
                            MESSAGE=None
                        )
                        log_embed.add_field(
                            name="🎯 Victim",
                            value=f"{target.display_name}",
                            inline=True
                        )
                        log_embed.add_field(
                            name="🏛️ Tax Paid",
                            value=f"₪{actual_tax:,}",
                            inline=True
                        )
                        await money_log.send(embed=log_embed)
                    
                    logger.info(f"Successful loot completed: ₪{target_cash:,} stolen, ₪{actual_tax:,} tax, ₪{net_received:,} received")
                    
                except Exception as e:
                    logger.error(f"Error during successful loot transaction: {e}")
                    await interaction.followup.send("⛔ An error occurred during the transaction.", ephemeral=True)
            
            else:
                # Failed theft - initiate combat
                logger.info(f"Failed loot: {looter.id} caught by {target.id}, initiating combat")
                
                # Create failure embed
                embed = self.create_loot_failure_embed(looter, target, stealth_result)
                
                # Send with target ping
                ping_message = f"{target.mention}"
                await interaction.followup.send(content=ping_message, embed=embed)
                
                # If target is conscious, give them a reaction window
                if target_stats['health'] > 0 and combat_reactions:
                    combat_reactions.set_reaction_window(target.id, looter.id, interaction.channel.id)
                    
                    # Send reaction prompt with ping
                    reaction_embed = combat_reactions.create_reaction_prompt_embed(target, looter)
                    reaction_embed.title = "🚨 Pickpocket Detected!"
                    reaction_embed.description = f"**{target.display_name}**, someone tried to steal from you!"
                    
                    ping_message = f"{target.mention}"
                    await interaction.followup.send(content=ping_message, embed=reaction_embed)
                
                logger.info("Failed loot completed, reaction window set")
            
        except Exception as e:
            logger.error(f"Unexpected error in loot command: {type(e).__name__}: {str(e)}", exc_info=True)
            try:
                if not interaction.response.is_done():
                    await interaction.response.send_message("⛔ An error occurred while processing the loot attempt.", ephemeral=True)
                else:
                    await interaction.followup.send("⛔ An error occurred while processing the loot attempt.", ephemeral=True)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {followup_error}")

async def setup(bot):
    try:
        await bot.add_cog(StatsLootCommands(bot))
        logger.info("✅ Stats Loot Commands cog loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load Stats Loot Commands cog: {type(e).__name__}: {str(e)}", exc_info=True)
        raise