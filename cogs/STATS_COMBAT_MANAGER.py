import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timedelta
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


class StatsCombatManager(commands.Cog):
    """Combat execution manager - orchestrates attacks and creates combat embeds"""
    
    def __init__(self, bot):
        self.bot = bot
        self.action_cooldowns = {}  # user_id: datetime when cooldown ends
    
    def get_combat_core(self):
        """Get the combat core cog"""
        return self.bot.get_cog('StatsCombatCore')
    
    def get_combat_reactions(self):
        """Get the combat reactions cog"""
        return self.bot.get_cog('StatsCombatReactions')
    
    def is_on_cooldown(self, user_id):
        """Check if user is on action cooldown"""
        if user_id not in self.action_cooldowns:
            return False
        
        cooldown_end = self.action_cooldowns[user_id]
        return datetime.now() < cooldown_end
    
    def set_cooldown(self, user_id):
        """Set 6-second action cooldown for user"""
        self.action_cooldowns[user_id] = datetime.now() + timedelta(seconds=6)
    
    def get_cooldown_remaining(self, user_id):
        """Get remaining cooldown time in seconds"""
        if user_id not in self.action_cooldowns:
            return 0
        
        remaining = self.action_cooldowns[user_id] - datetime.now()
        return max(0, remaining.total_seconds())
    
    def create_combat_embed(self, attacker, defender, attacker_stats, defender_stats, attack_result, damage, new_health, action_type="Attack"):
        """Create combat result embed"""
        embed = discord.Embed(
            title=f"⚔️ {action_type}",
            color=0xff0000 if attack_result['hit'] else 0x808080,
            timestamp=discord.utils.utcnow()
        )
        
        # Attack details
        if attack_result['critical_hit']:
            attack_desc = f"🎯 **CRITICAL HIT!** Natural 20!"
        elif attack_result['critical_miss']:
            attack_desc = f"💥 **CRITICAL MISS!** Natural 1!"
        elif attack_result['hit']:
            attack_desc = f"✅ **Hit!** ({attack_result['roll']} + {attack_result['attack_bonus']} = {attack_result['total']} vs AC {attack_result['target_ac']})"
        else:
            attack_desc = f"❌ **Miss!** ({attack_result['roll']} + {attack_result['attack_bonus']} = {attack_result['total']} vs AC {attack_result['target_ac']})"
        
        embed.add_field(name="🎲 Attack Roll", value=attack_desc, inline=False)
        
        # Damage and health
        if attack_result['hit']:
            damage_text = f"💔 **{damage} damage** dealt"
            if attack_result['critical_hit']:
                damage_text += " (critical damage!)"
            
            health_status = "💀 **UNCONSCIOUS**" if new_health <= 0 else f"❤️ {new_health} HP"
            embed.add_field(name="💥 Damage", value=damage_text, inline=True)
            embed.add_field(name="🩺 Health", value=health_status, inline=True)
        
        # Combatants current status
        attacker_hp = attacker_stats.get('health', 0)
        defender_hp = new_health if attack_result['hit'] else defender_stats.get('health', 0)
        
        attacker_status = "💀" if attacker_hp <= 0 else f"❤️{attacker_hp}"
        defender_status = "💀" if defender_hp <= 0 else f"❤️{defender_hp}"
        
        embed.add_field(
            name="👥 Participants",
            value=f"⚔️ **{attacker.display_name}** {attacker_status}\n🛡️ **{defender.display_name}** {defender_status}",
            inline=False
        )
        
        return embed
    
    async def execute_attack(self, attacker_id, defender_id, channel_id, is_automatic=False, is_reaction=False):
        """Execute an attack between two players"""
        combat_core = self.get_combat_core()
        combat_reactions = self.get_combat_reactions()
        
        if not combat_core:
            logging.error("Combat core not available")
            return
        
        stats_core = combat_core.get_stats_core()
        if not stats_core:
            logging.error("Stats core not available")
            return
        
        attacker_stats = stats_core.get_user_stats(attacker_id)
        defender_stats = stats_core.get_user_stats(defender_id)
        
        if not attacker_stats or not defender_stats:
            logging.error("Could not get stats for combat participants")
            return
        
        # Make attack
        attack_result = combat_core.make_attack_roll(attacker_stats, defender_stats)
        
        new_health = defender_stats['health']
        damage = 0
        
        if attack_result['hit']:
            damage = combat_core.calculate_damage(attacker_stats)
            if attack_result['critical_hit']:
                damage *= 2  # Critical hits double damage
            
            old_health = defender_stats['health']
            new_health = combat_core.apply_damage(defender_id, damage)
            
            # Handle stabilization system integration
            stabilization_system = combat_core.get_stabilization_system()
            if stabilization_system and old_health <= 0 and new_health is not None:
                # Taking damage while unconscious adds failures
                if attack_result['critical_hit']:
                    stabilization_system.add_stabilization_failure(defender_id, 2)  # Crit = 2 failures
                else:
                    stabilization_system.add_stabilization_failure(defender_id, 1)  # Normal = 1 failure
            elif stabilization_system and old_health > 0 and new_health <= 0:
                # Just became unconscious - start stabilization
                stabilization_system.start_stabilization(defender_id)
        
        # Log the combat action
        combat_core.log_combat_action(attacker_id, defender_id, damage, attack_result['hit'], attack_result['critical_hit'])
        
        # Send combat result
        channel = self.bot.get_channel(channel_id)
        if channel:
            attacker = self.bot.get_user(attacker_id)
            defender = self.bot.get_user(defender_id)
            
            # Determine action type for embed
            if is_automatic:
                action_type = "Automatic Retaliation"
            elif is_reaction:
                action_type = "Retaliation"
            else:
                action_type = "Attack"
            
            embed = self.create_combat_embed(
                attacker, defender,
                attacker_stats, defender_stats,
                attack_result, damage, new_health, action_type
            )
            
            if is_automatic:
                embed.description = f"⏰ **{attacker.display_name}** took too long and automatically retaliates against **{defender.display_name}**!"
            elif is_reaction:
                embed.description = f"⚡ **{attacker.display_name}** retaliates against **{defender.display_name}**!"
            else:
                embed.description = f"⚔️ **{attacker.display_name}** attacks **{defender.display_name}**!"
            
            # Ping the defender when they're attacked
            ping_message = f"{defender.mention}"
            await channel.send(content=ping_message, embed=embed)
        
        # Set attacker's cooldown
        self.set_cooldown(attacker_id)
        
        # Clear any pending reaction for the attacker (they acted)
        if combat_reactions:
            combat_reactions.clear_reaction(attacker_id)
        
        # If defender is conscious and this wasn't a reaction, give them a reaction window
        if new_health > 0 and not is_reaction and not is_automatic and combat_reactions:
            combat_reactions.set_reaction_window(defender_id, attacker_id, channel_id)
            
            # Send reaction prompt with ping
            if channel:
                embed = combat_reactions.create_reaction_prompt_embed(defender, attacker)
                ping_message = f"{defender.mention}"
                await channel.send(content=ping_message, embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCombatManager(bot))
    logging.info("✅ Stats Combat Manager cog loaded successfully")