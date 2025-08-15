import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, timedelta
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


class StatsCombatReactions(commands.Cog):
    """Combat reaction system - handles 6-second reaction windows and automatic retaliation"""
    
    def __init__(self, bot):
        self.bot = bot
        self.pending_reactions = {}  # user_id: {'attacker_id': int, 'timeout': datetime, 'channel_id': int}
        self.reaction_timeout_loop.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.reaction_timeout_loop.cancel()
    
    def get_combat_core(self):
        """Get the combat core cog"""
        return self.bot.get_cog('StatsCombatCore')
    
    def get_combat_manager(self):
        """Get the combat manager cog"""
        return self.bot.get_cog('StatsCombatManager')
    
    def set_reaction_window(self, defender_id, attacker_id, channel_id):
        """Set 6-second reaction window for defender"""
        self.pending_reactions[defender_id] = {
            'attacker_id': attacker_id,
            'timeout': datetime.now() + timedelta(seconds=6),
            'channel_id': channel_id
        }
    
    def has_pending_reaction(self, user_id):
        """Check if user has a pending reaction"""
        return user_id in self.pending_reactions
    
    def get_pending_reaction(self, user_id):
        """Get pending reaction data for user"""
        return self.pending_reactions.get(user_id)
    
    def clear_reaction(self, user_id):
        """Clear pending reaction for user"""
        if user_id in self.pending_reactions:
            del self.pending_reactions[user_id]
    
    def create_reaction_prompt_embed(self, defender, attacker):
        """Create embed prompting for reaction"""
        embed = discord.Embed(
            title="⚡ You're Under Attack!",
            description=f"**{defender.display_name}**, you have 6 seconds to react!",
            color=0xff6600
        )
        
        embed.add_field(
            name="🎯 Available Actions",
            value=f"• `/attack @{attacker.display_name}` - Retaliate against your attacker\n• `/attack @someone_else` - Attack a different target\n• `/retreat` - Flee from the situation",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Time Limit",
            value="If no action is taken in 6 seconds, you will automatically retaliate!",
            inline=False
        )
        
        embed.set_footer(text=f"Attacked by {attacker.display_name}")
        
        return embed
    
    async def execute_automatic_retaliation(self, defender_id):
        """Execute automatic retaliation when reaction times out"""
        reaction_data = self.get_pending_reaction(defender_id)
        if not reaction_data:
            return
        
        attacker_id = reaction_data['attacker_id']
        channel_id = reaction_data['channel_id']
        
        # Clear the reaction
        self.clear_reaction(defender_id)
        
        # Check if defender is still conscious
        combat_core = self.get_combat_core()
        if combat_core:
            stats_core = combat_core.get_stats_core()
            if stats_core:
                defender_stats = stats_core.get_user_stats(defender_id)
                if defender_stats and defender_stats['health'] <= 0:
                    # Defender is unconscious, can't retaliate
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        defender = self.bot.get_user(defender_id)
                        embed = discord.Embed(
                            title="💀 No Retaliation",
                            description=f"**{defender.display_name}** is unconscious and cannot retaliate!",
                            color=0x808080
                        )
                        await channel.send(embed=embed)
                    return
        
        # Execute automatic retaliation via combat manager
        combat_manager = self.get_combat_manager()
        if combat_manager:
            await combat_manager.execute_attack(defender_id, attacker_id, channel_id, is_automatic=True, is_reaction=True)
    
    @tasks.loop(seconds=1)
    async def reaction_timeout_loop(self):
        """Check for reaction timeouts and execute automatic retaliations"""
        current_time = datetime.now()
        expired_reactions = []
        
        for defender_id, reaction_data in self.pending_reactions.items():
            if current_time >= reaction_data['timeout']:
                expired_reactions.append(defender_id)
        
        for defender_id in expired_reactions:
            try:
                await self.execute_automatic_retaliation(defender_id)
            except Exception as e:
                logging.error(f"❌ Error in reaction timeout: {e}")
                # Clean up the expired reaction
                self.clear_reaction(defender_id)
    
    @reaction_timeout_loop.before_loop
    async def before_reaction_timeout_loop(self):
        """Wait until the bot is ready before starting the loop"""
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="retreat", description="Retreat from combat (clear any pending reactions)")
    @app_commands.guilds(GUILD)
    async def retreat(self, interaction: discord.Interaction):
        """Retreat from any pending combat reactions"""
        user_id = interaction.user.id
        
        if not self.has_pending_reaction(user_id):
            await interaction.response.send_message("❌ You have no pending reactions to retreat from!", ephemeral=True)
            return
        
        # Clear the reaction
        reaction_data = self.get_pending_reaction(user_id)
        self.clear_reaction(user_id)
        
        # Send retreat message
        embed = discord.Embed(
            title="🏃 Retreat",
            description=f"**{interaction.user.display_name}** has retreated from combat!",
            color=0xffff00,
            timestamp=discord.utils.utcnow()
        )
        
        if reaction_data:
            attacker = self.bot.get_user(reaction_data['attacker_id'])
            if attacker:
                embed.add_field(
                    name="🛡️ Avoided Retaliation",
                    value=f"Chose not to retaliate against **{attacker.display_name}**",
                    inline=False
                )
        
        embed.set_footer(text="Sometimes discretion is the better part of valor!")
        
        await interaction.response.send_message(embed=embed)
        
        logging.info(f"{interaction.user.display_name} retreated from combat")

async def setup(bot):
    await bot.add_cog(StatsCombatReactions(bot))
    logging.info("✅ Stats Combat Reactions cog loaded successfully")