import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import random
import logging
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


class StatsCombat(commands.Cog):
    """D&D-style combat system for character battles"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_combats = {}  # combat_id: combat_data
        self.action_cooldowns = {}  # user_id: datetime
        self.pending_turns = {}  # user_id: turn_data with timeout
        self.init_database()
        self.turn_timeout_loop.start()
    
    def cog_unload(self):
        """Clean up when cog is unloaded"""
        self.turn_timeout_loop.cancel()
    
    def init_database(self):
        """Initialize combat tracking database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Create combat log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS combat_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_id INTEGER,
                    defender_id INTEGER,
                    attacker_name TEXT,
                    defender_name TEXT,
                    winner_id INTEGER,
                    rounds INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("✅ Combat database initialized successfully")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize combat database: {e}")
    
    def get_stats_core(self):
        """Get the StatsCore cog for accessing core functionality"""
        return self.bot.get_cog('StatsCore')
    
    def calculate_attack_bonus(self, stats):
        """Calculate attack bonus (STR modifier for unarmed)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return 0
        return stats_core.get_constitution_modifier(stats.get('strength', 10))
    
    def calculate_armor_class(self, stats):
        """Calculate AC (10 + DEX modifier for unarmored)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return 10
        dex_mod = stats_core.get_constitution_modifier(stats.get('dexterity', 10))
        return 10 + dex_mod
    
    def calculate_damage(self, stats):
        """Calculate unarmed damage (1 + STR modifier, minimum 1)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return 1
        str_mod = stats_core.get_constitution_modifier(stats.get('strength', 10))
        return max(1, 1 + str_mod)
    
    def get_stabilization_system(self):
        """Get the StabilizationSystem cog"""
        return self.bot.get_cog('StabilizationSystem')
    
    def get_hospital_system(self):
        """Get the HospitalSystem cog"""
        return self.bot.get_cog('HospitalSystem')
    
    def is_user_in_hospital(self, user_id):
        """Check if user is in hospital"""
        hospital_system = self.get_hospital_system()
        if hospital_system and hasattr(hospital_system, 'is_in_hospital'):
            return hospital_system.is_in_hospital(user_id)
        return False
    
    def make_stealth_check(self, looter_stats, target_stats):
        """Make a stealth check (DEX-based) vs target's perception (WIS-based)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return {'success': False, 'stealth_roll': 1, 'dex_modifier': 0, 'stealth_total': 1, 'passive_perception': 10}
        
        # Looter rolls stealth (1d20 + DEX modifier)
        stealth_roll = random.randint(1, 20)
        dex_mod = stats_core.get_constitution_modifier(looter_stats.get('dexterity', 10))
        stealth_total = stealth_roll + dex_mod
        
        # Target's passive perception (10 + WIS modifier)
        wis_mod = stats_core.get_constitution_modifier(target_stats.get('wisdom', 10))
        passive_perception = 10 + wis_mod
        
        success = stealth_total >= passive_perception
        
        return {
            'stealth_roll': stealth_roll,
            'dex_modifier': dex_mod,
            'stealth_total': stealth_total,
            'passive_perception': passive_perception,
            'success': success
        }
    
    def make_attack_roll(self, attacker_stats, defender_stats):
        """Make an attack roll against target AC"""
        # Roll 1d20 + attack bonus
        roll = random.randint(1, 20)
        attack_bonus = self.calculate_attack_bonus(attacker_stats)
        total_attack = roll + attack_bonus
        
        # Calculate target AC
        target_ac = self.calculate_armor_class(defender_stats)
        
        # Check for critical hit (natural 20) or critical miss (natural 1)
        critical_hit = (roll == 20)
        critical_miss = (roll == 1)
        
        # Determine if attack hits
        hit = total_attack >= target_ac or critical_hit
        if critical_miss:
            hit = False
        
        return {
            'roll': roll,
            'attack_bonus': attack_bonus,
            'total': total_attack,
            'target_ac': target_ac,
            'hit': hit,
            'critical_hit': critical_hit,
            'critical_miss': critical_miss
        }
    
    def apply_damage(self, user_id, damage):
        """Apply damage to a user and update their health in the database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Get current health
            cursor.execute('SELECT health FROM user_stats WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            current_health = result[0]
            new_health = current_health - damage
            
            # Update health (can go negative)
            cursor.execute('UPDATE user_stats SET health = ? WHERE user_id = ?', (new_health, user_id))
            conn.commit()
            conn.close()
            
            return new_health
            
        except Exception as e:
            logging.error(f"❌ Failed to apply damage: {e}")
            return None
    
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
    
    def is_user_in_combat(self, user_id):
        """Check if user is involved in any combat"""
        for combat_data in self.active_combats.values():
            if user_id in [combat_data['player1_id'], combat_data['player2_id']]:
                return True
        return False
    
    def get_combat_by_user(self, user_id):
        """Get combat data where user is involved"""
        for combat_id, combat_data in self.active_combats.items():
            if user_id in [combat_data['player1_id'], combat_data['player2_id']]:
                return combat_id, combat_data
        return None, None
    
    def get_opponent_id(self, combat_data, user_id):
        """Get the opponent's ID in a combat"""
        if combat_data['player1_id'] == user_id:
            return combat_data['player2_id']
        else:
            return combat_data['player1_id']
    
    def log_combat(self, attacker_id, defender_id, attacker_name, defender_name, winner_id, rounds):
        """Log combat result to database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO combat_log (attacker_id, defender_id, attacker_name, defender_name, winner_id, rounds)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (attacker_id, defender_id, attacker_name, defender_name, winner_id, rounds))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ Failed to log combat: {e}")
    
    def create_combat_embed(self, attacker, defender, attacker_stats, defender_stats, attack_result, damage, new_health, round_num, action_type="Attack"):
        """Create combat result embed"""
        embed = discord.Embed(
            title=f"⚔️ {action_type} - Round {round_num}",
            color=0xff0000 if attack_result['hit'] else 0x808080
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
        
        # Combatants
        attacker_hp = attacker_stats.get('health', 0)
        defender_hp = new_health if attack_result['hit'] else defender_stats.get('health', 0)
        
        attacker_status = "💀" if attacker_hp <= 0 else f"❤️{attacker_hp}"
        defender_status = "💀" if defender_hp <= 0 else f"❤️{defender_hp}"
        
        embed.add_field(
            name="👥 Combatants",
            value=f"⚔️ **{attacker.display_name}** {attacker_status}\n🛡️ **{defender.display_name}** {defender_status}",
            inline=False
        )
        
        return embed
    
    def create_turn_prompt_embed(self, current_player, opponent, combat_data):
        """Create embed prompting for action"""
        embed = discord.Embed(
            title="⚡ Your Turn!",
            description=f"**{current_player.display_name}**, you have 6 seconds to choose an action!",
            color=0xffff00
        )
        
        embed.add_field(
            name="🎯 Available Actions",
            value="• `/combat_attack` - Attack your opponent\n• `/retreat` - Flee from combat",
            inline=False
        )
        
        embed.add_field(
            name="⏰ Time Limit",
            value="If no action is taken in 6 seconds, you will automatically attack!",
            inline=False
        )
        
        embed.set_footer(text=f"Round {combat_data['round']} • Combat vs {opponent.display_name}")
        
        return embed
    
    async def execute_automatic_action(self, user_id):
        """Execute automatic attack when turn times out"""
        combat_id, combat_data = self.get_combat_by_user(user_id)
        if not combat_id or not combat_data:
            return
        
        opponent_id = self.get_opponent_id(combat_data, user_id)
        
        # Get stats
        stats_core = self.get_stats_core()
        if not stats_core:
            return
        
        attacker_stats = stats_core.get_user_stats(user_id)
        defender_stats = stats_core.get_user_stats(opponent_id)
        
        if not attacker_stats or not defender_stats:
            return
        
        # Can't act if unconscious
        if attacker_stats['health'] <= 0:
            # End their turn without action
            await self.end_turn(combat_id, combat_data, None)
            return
        
        # Execute automatic attack
        await self.execute_attack(user_id, opponent_id, combat_id, combat_data, is_automatic=True)
    
    async def execute_attack(self, attacker_id, defender_id, combat_id, combat_data, is_automatic=False):
        """Execute an attack between two players"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return
        
        attacker_stats = stats_core.get_user_stats(attacker_id)
        defender_stats = stats_core.get_user_stats(defender_id)
        
        if not attacker_stats or not defender_stats:
            return
        
        # Make attack
        attack_result = self.make_attack_roll(attacker_stats, defender_stats)
        
        new_health = defender_stats['health']
        damage = 0
        
        if attack_result['hit']:
            damage = self.calculate_damage(attacker_stats)
            if attack_result['critical_hit']:
                damage *= 2  # Critical hits double damage
            
            old_health = defender_stats['health']
            new_health = self.apply_damage(defender_id, damage)
            
            # Handle stabilization system integration
            stabilization_system = self.get_stabilization_system()
            if stabilization_system and old_health <= 0 and new_health is not None:
                # Taking damage while unconscious adds failures
                if attack_result['critical_hit']:
                    stabilization_system.add_stabilization_failure(defender_id, 2)  # Crit = 2 failures
                else:
                    stabilization_system.add_stabilization_failure(defender_id, 1)  # Normal = 1 failure
            elif stabilization_system and old_health > 0 and new_health <= 0:
                # Just became unconscious - start stabilization
                stabilization_system.start_stabilization(defender_id)
        
        # Send combat result
        channel = self.bot.get_channel(combat_data['channel_id'])
        if channel:
            attacker = self.bot.get_user(attacker_id)
            defender = self.bot.get_user(defender_id)
            
            action_type = "Automatic Attack" if is_automatic else "Attack"
            embed = self.create_combat_embed(
                attacker, defender,
                attacker_stats, defender_stats,
                attack_result, damage, new_health, combat_data['round'], action_type
            )
            
            if is_automatic:
                embed.description = f"⏰ **{attacker.display_name}** took too long and automatically attacks!"
            else:
                embed.description = f"⚔️ **{attacker.display_name}** attacks **{defender.display_name}**!"
            
            await channel.send(embed=embed)
        
        # Set attacker's cooldown
        self.set_cooldown(attacker_id)
        
        # Check if combat should end
        if new_health <= 0:
            await self.end_combat(combat_id, combat_data, attacker_id)
        else:
            await self.end_turn(combat_id, combat_data, channel)
    
    async def end_turn(self, combat_id, combat_data, channel):
        """End current turn and start next player's turn"""
        # Switch to next player's turn
        if combat_data['current_turn'] == combat_data['player1_id']:
            next_player_id = combat_data['player2_id']
        else:
            next_player_id = combat_data['player1_id']
        
        combat_data['current_turn'] = next_player_id
        combat_data['round'] += 1
        
        # Start next turn
        await self.start_turn(next_player_id, combat_data, channel)
    
    async def start_turn(self, player_id, combat_data, channel):
        """Start a player's turn with 6-second timeout"""
        opponent_id = self.get_opponent_id(combat_data, player_id)
        
        # Get current stats to check if player is conscious
        stats_core = self.get_stats_core()
        if stats_core:
            player_stats = stats_core.get_user_stats(player_id)
            if player_stats and player_stats['health'] <= 0:
                # Player is unconscious, skip their turn
                if channel:
                    player = self.bot.get_user(player_id)
                    embed = discord.Embed(
                        title="💀 Turn Skipped",
                        description=f"**{player.display_name}** is unconscious and cannot act!",
                        color=0x808080
                    )
                    await channel.send(embed=embed)
                
                # Continue to next turn
                await self.end_turn(combat_data.get('combat_id'), combat_data, channel)
                return
        
        # Set up turn timeout
        turn_data = {
            'player_id': player_id,
            'combat_id': combat_data.get('combat_id'),
            'timeout': datetime.now() + timedelta(seconds=6)
        }
        self.pending_turns[player_id] = turn_data
        
        # Send turn prompt
        if channel:
            player = self.bot.get_user(player_id)
            opponent = self.bot.get_user(opponent_id)
            
            embed = self.create_turn_prompt_embed(player, opponent, combat_data)
            await channel.send(embed=embed)
    
    async def end_combat(self, combat_id, combat_data, winner_id):
        """End combat and declare winner"""
        channel = self.bot.get_channel(combat_data['channel_id'])
        
        if channel:
            winner = self.bot.get_user(winner_id)
            loser_id = self.get_opponent_id(combat_data, winner_id)
            loser = self.bot.get_user(loser_id)
            
            embed = discord.Embed(
                title="🏆 Combat Ended",
                description=f"**{winner.display_name}** is victorious!",
                color=0x00ff00
            )
            
            # Get final health stats
            stats_core = self.get_stats_core()
            if stats_core:
                winner_stats = stats_core.get_user_stats(winner_id)
                loser_stats = stats_core.get_user_stats(loser_id)
                
                if winner_stats and loser_stats:
                    embed.add_field(
                        name="📊 Final Status",
                        value=f"🏆 **{winner.display_name}**: {max(0, winner_stats['health'])} HP\n💀 **{loser.display_name}**: {min(0, loser_stats['health'])} HP",
                        inline=False
                    )
            
            embed.set_footer(text=f"Combat lasted {combat_data['round']} rounds")
            await channel.send(embed=embed)
            
            # Log combat
            self.log_combat(
                combat_data['player1_id'], combat_data['player2_id'],
                self.bot.get_user(combat_data['player1_id']).display_name,
                self.bot.get_user(combat_data['player2_id']).display_name,
                winner_id, combat_data['round']
            )
        
        # Clean up
        if combat_id in self.active_combats:
            del self.active_combats[combat_id]
        
        # Remove any pending turns for both players
        for player_id in [combat_data['player1_id'], combat_data['player2_id']]:
            if player_id in self.pending_turns:
                del self.pending_turns[player_id]
    
    @tasks.loop(seconds=1)
    async def turn_timeout_loop(self):
        """Check for turn timeouts and execute automatic actions"""
        current_time = datetime.now()
        expired_turns = []
        
        for player_id, turn_data in self.pending_turns.items():
            if current_time >= turn_data['timeout']:
                expired_turns.append(player_id)
        
        for player_id in expired_turns:
            try:
                await self.execute_automatic_action(player_id)
                if player_id in self.pending_turns:
                    del self.pending_turns[player_id]
            except Exception as e:
                logging.error(f"❌ Error in turn timeout: {e}")
                if player_id in self.pending_turns:
                    del self.pending_turns[player_id]
    
    @app_commands.command(name="attack", description="Attack another user in unarmed combat")
    @app_commands.describe(target="The user to attack")
    @app_commands.guilds(GUILD)
    async def attack(self, interaction: discord.Interaction, target: discord.Member):
        """Initiate combat with another user"""
        attacker = interaction.user
        
        # Basic validation
        if target == attacker:
            await interaction.response.send_message("❌ You cannot attack yourself!", ephemeral=True)
            return
        
        if target.bot:
            await interaction.response.send_message("❌ You cannot attack bots!", ephemeral=True)
            return
        
        # Check cooldown
        if self.is_on_cooldown(attacker.id):
            remaining = self.get_cooldown_remaining(attacker.id)
            await interaction.response.send_message(f"❌ You're still on cooldown! Wait {remaining:.1f} more seconds.", ephemeral=True)
            return
        
        # Check if either user is already in combat
        if self.is_user_in_combat(attacker.id):
            await interaction.response.send_message("❌ You're already in combat!", ephemeral=True)
            return
        
        if self.is_user_in_combat(target.id):
            await interaction.response.send_message("❌ That user is already in combat!", ephemeral=True)
            return
        
        # Get stats
        stats_core = self.get_stats_core()
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
        if self.is_user_in_hospital(target.id):
            await interaction.response.send_message("❌ You cannot attack someone who is in the hospital!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Create combat
        combat_id = f"{attacker.id}_{target.id}_{int(datetime.now().timestamp())}"
        combat_data = {
            'combat_id': combat_id,
            'player1_id': attacker.id,
            'player2_id': target.id,
            'current_turn': attacker.id,
            'channel_id': interaction.channel.id,
            'round': 1
        }
        
        self.active_combats[combat_id] = combat_data
        
        # Execute initial attack
        await self.execute_attack(attacker.id, target.id, combat_id, combat_data)
    
    @app_commands.command(name="combat_attack", description="Attack your opponent during your turn")
    @app_commands.guilds(GUILD)
    async def combat_attack(self, interaction: discord.Interaction):
        """Attack during active combat turn"""
        user_id = interaction.user.id
        
        # Check if it's user's turn
        if user_id not in self.pending_turns:
            await interaction.response.send_message("❌ It's not your turn or you're not in combat!", ephemeral=True)
            return
        
        # Check cooldown
        if self.is_on_cooldown(user_id):
            remaining = self.get_cooldown_remaining(user_id)
            await interaction.response.send_message(f"❌ You're still on cooldown! Wait {remaining:.1f} more seconds.", ephemeral=True)
            return
        
        combat_id, combat_data = self.get_combat_by_user(user_id)
        if not combat_id or not combat_data:
            await interaction.response.send_message("❌ Combat data not found!", ephemeral=True)
            return
        
        # Check if user is conscious
        stats_core = self.get_stats_core()
        if stats_core:
            user_stats = stats_core.get_user_stats(user_id)
            if user_stats and user_stats['health'] <= 0:
                await interaction.response.send_message("❌ You are unconscious and cannot take actions!", ephemeral=True)
                return
        
        await interaction.response.defer()
        
        # Remove pending turn
        if user_id in self.pending_turns:
            del self.pending_turns[user_id]
        
        opponent_id = self.get_opponent_id(combat_data, user_id)
        
        # Execute attack
        await self.execute_attack(user_id, opponent_id, combat_id, combat_data)
    
    @app_commands.command(name="retreat", description="Retreat from combat")
    @app_commands.guilds(GUILD)
    async def retreat(self, interaction: discord.Interaction):
        """Retreat from active combat"""
        user_id = interaction.user.id
        
        combat_id, combat_data = self.get_combat_by_user(user_id)
        if not combat_id or not combat_data:
            await interaction.response.send_message("❌ You're not in active combat!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        opponent_id = self.get_opponent_id(combat_data, user_id)
        opponent = self.bot.get_user(opponent_id)
        
        # Send retreat message
        embed = discord.Embed(
            title="🏃 Combat Ended - Retreat",
            description=f"**{interaction.user.display_name}** has retreated from combat!",
            color=0xffff00
        )
        embed.set_footer(text=f"Combat lasted {combat_data['round']} rounds")
        
        await interaction.followup.send(embed=embed)
        
        # Log combat (no winner for retreats)
        self.log_combat(
            combat_data['player1_id'], combat_data['player2_id'],
            self.bot.get_user(combat_data['player1_id']).display_name,
            self.bot.get_user(combat_data['player2_id']).display_name,
            None, combat_data['round']
        )
        
        # Clean up combat
        if combat_id in self.active_combats:
            del self.active_combats[combat_id]
        
        # Remove any pending turns for both players
        for player_id in [combat_data['player1_id'], combat_data['player2_id']]:
            if player_id in self.pending_turns:
                del self.pending_turns[player_id]
    
    @app_commands.command(name="loot", description="Attempt to loot cash from another user")
    @app_commands.describe(target="The user to loot from")
    @app_commands.guilds(GUILD)
    async def loot(self, interaction: discord.Interaction, target: discord.Member):
        """Attempt to loot another user"""
        looter = interaction.user
        
        # Basic validation
        if target == looter:
            await interaction.response.send_message("❌ You cannot loot yourself!", ephemeral=True)
            return
        
        if target.bot:
            await interaction.response.send_message("❌ You cannot loot bots!", ephemeral=True)
            return
        
        # Check if looter is in combat
        if self.is_user_in_combat(looter.id):
            await interaction.response.send_message("❌ You cannot loot while in combat!", ephemeral=True)
            return
        
        # Check if target is in combat
        if self.is_user_in_combat(target.id):
            await interaction.response.send_message("❌ You cannot loot someone who is in combat!", ephemeral=True)
            return
        
        # Check cooldown
        if self.is_on_cooldown(looter.id):
            remaining = self.get_cooldown_remaining(looter.id)
            await interaction.response.send_message(f"❌ You're still on cooldown! Wait {remaining:.1f} more seconds.", ephemeral=True)
            return
        
        # Get stats
        stats_core = self.get_stats_core()
        if not stats_core:
            await interaction.response.send_message("❌ Stats system not available.", ephemeral=True)
            return
        
        looter_stats = stats_core.get_user_stats(looter.id)
        target_stats = stats_core.get_user_stats(target.id)
        
        if not looter_stats:
            await interaction.response.send_message("❌ You don't have character stats yet!", ephemeral=True)
            return
        
        if not target_stats:
            await interaction.response.send_message("❌ That user doesn't have character stats yet!", ephemeral=True)
            return
        
        # Check if looter is unconscious
        if looter_stats['health'] <= 0:
            await interaction.response.send_message("❌ You are unconscious and cannot take actions!", ephemeral=True)
            return
        
        # Check if target is in hospital
        if self.is_user_in_hospital(target.id):
            await interaction.response.send_message("❌ You cannot loot someone who is in the hospital!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Import economy functions
        try:
            from SHEKELS.BALANCE import BALANCE
            from SHEKELS.TRANSFERS import UPDATE_BALANCE
            
            # Get target's cash
            target_balance = BALANCE(target)
            target_cash = target_balance[0]
            
            if target_cash <= 0:
                await interaction.followup.send(f"❌ {target.display_name} has no cash to loot!")
                return
            
            # Check if target is unconscious
            if target_stats['health'] <= 0:
                # Automatic success - loot all cash
                try:
                    # Calculate tax if looter is subject to taxation and amount >= 100
                    import json
                    import math
                    
                    USER_DATA = 'SHEKELS/USER_DATA.JSON'
                    with open(USER_DATA, 'r') as file:
                        DATA = json.load(file)
                    
                    looter_id_str = str(looter.id)
                    initial_tax = 0
                    
                    if (looter_id_str in DATA and 
                        DATA[looter_id_str].get("TAX", True) and 
                        target_cash >= 100):
                        initial_tax = int(math.floor(target_cash/100)*10)
                    
                    # Use tax credits to reduce the tax
                    credits_used = 0
                    actual_tax = initial_tax
                    if initial_tax > 0:
                        from SHEKELS.BALANCE import USE_TAX_CREDITS
                        credits_used, actual_tax = USE_TAX_CREDITS(looter, initial_tax)
                    
                    # Calculate actual cash received after tax
                    cash_received = target_cash - actual_tax
                    
                    # Transfer cash
                    UPDATE_BALANCE(target, -target_cash, "CASH")
                    UPDATE_BALANCE(looter, cash_received, "CASH")
                    
                    # Pay taxes to treasury if applicable
                    if actual_tax > 0:
                        from SHEKELS.TREASURY import pay_treasury
                        pay_treasury(actual_tax)
                    
                    embed = discord.Embed(
                        title="💰 Looting Successful",
                        description=f"**{looter.display_name}** looted **{target.display_name}**!",
                        color=0x00ff00
                    )
                    
                    embed.add_field(
                        name="💵 Cash Stolen",
                        value=f"₪{target_cash:,}",
                        inline=True
                    )
                    
                    if initial_tax > 0:
                        if credits_used > 0:
                            embed.add_field(
                                name="💳 Tax Credits Used",
                                value=f"₪{credits_used:,}",
                                inline=True
                            )
                        
                        if actual_tax > 0:
                            embed.add_field(
                                name="💸 Tax Paid",
                                value=f"₪{actual_tax:,}",
                                inline=True
                            )
                        
                        embed.add_field(
                            name="💰 Cash Received",
                            value=f"₪{cash_received:,}",
                            inline=True
                        )
                    else:
                        embed.add_field(
                            name="😴 Target Status",
                            value="Unconscious (no resistance)",
                            inline=True
                        )
                    
                    footer_text = "Easy pickings from an unconscious target!"
                    if initial_tax > 0:
                        if credits_used > 0 and actual_tax > 0:
                            footer_text += f" • ₪{credits_used:,} credits used, ₪{actual_tax:,} tax paid"
                        elif credits_used > 0:
                            footer_text += f" • ₪{credits_used:,} credits covered all taxes"
                        else:
                            footer_text += f" • Paid ₪{actual_tax:,} in taxes"
                    embed.set_footer(text=footer_text)
                    
                    await interaction.followup.send(embed=embed)
                    
                    # Set cooldown
                    self.set_cooldown(looter.id)
                    
                    if initial_tax > 0:
                        logging.info(f"{looter.display_name} looted ₪{target_cash} from unconscious {target.display_name}, used ₪{credits_used} credits, paid ₪{actual_tax} in taxes")
                    else:
                        logging.info(f"{looter.display_name} looted ₪{target_cash} from unconscious {target.display_name}")
                    
                except Exception as e:
                    logging.error(f"❌ Failed to transfer looted money: {e}")
                    await interaction.followup.send("❌ Failed to complete the looting. Please try again.", ephemeral=True)
                
            else:
                # Target is conscious - stealth check required
                stealth_result = self.make_stealth_check(looter_stats, target_stats)
                
                if stealth_result['success']:
                    # Successful stealth - loot all cash without triggering combat
                    try:
                        # Calculate tax if looter is subject to taxation and amount >= 100
                        import json
                        import math
                        
                        USER_DATA = 'SHEKELS/USER_DATA.JSON'
                        with open(USER_DATA, 'r') as file:
                            DATA = json.load(file)
                        
                        looter_id_str = str(looter.id)
                        initial_tax = 0
                        
                        if (looter_id_str in DATA and 
                            DATA[looter_id_str].get("TAX", True) and 
                            target_cash >= 100):
                            initial_tax = int(math.floor(target_cash/100)*10)
                        
                        # Use tax credits to reduce the tax
                        credits_used = 0
                        actual_tax = initial_tax
                        if initial_tax > 0:
                            from SHEKELS.BALANCE import USE_TAX_CREDITS
                            credits_used, actual_tax = USE_TAX_CREDITS(looter, initial_tax)
                        
                        # Calculate actual cash received after tax
                        cash_received = target_cash - actual_tax
                        
                        # Transfer cash
                        UPDATE_BALANCE(target, -target_cash, "CASH")
                        UPDATE_BALANCE(looter, cash_received, "CASH")
                        
                        # Pay taxes to treasury if applicable
                        if actual_tax > 0:
                            from SHEKELS.TREASURY import pay_treasury
                            pay_treasury(actual_tax)
                        
                        embed = discord.Embed(
                            title="🥷 Stealth Looting Successful",
                            description=f"**{looter.display_name}** stealthily looted **{target.display_name}**!",
                            color=0x9932cc
                        )
                        
                        stealth_desc = f"🎲 **Stealth Check:** {stealth_result['stealth_roll']} + {stealth_result['dex_modifier']} = {stealth_result['stealth_total']}"
                        stealth_desc += f"\n🔍 **vs Perception:** {stealth_result['passive_perception']}"
                        
                        embed.add_field(
                            name="🎯 Stealth Roll",
                            value=stealth_desc,
                            inline=False
                        )
                        
                        embed.add_field(
                            name="💵 Cash Stolen",
                            value=f"₪{target_cash:,}",
                            inline=True
                        )
                        
                        if initial_tax > 0:
                            if credits_used > 0:
                                embed.add_field(
                                    name="💳 Tax Credits Used",
                                    value=f"₪{credits_used:,}",
                                    inline=True
                                )
                            
                            if actual_tax > 0:
                                embed.add_field(
                                    name="💸 Tax Paid",
                                    value=f"₪{actual_tax:,}",
                                    inline=True
                                )
                            
                            embed.add_field(
                                name="💰 Cash Received",
                                value=f"₪{cash_received:,}",
                                inline=True
                            )
                            
                            embed.add_field(
                                name="😴 Detection",
                                value="Undetected!",
                                inline=True
                            )
                        else:
                            embed.add_field(
                                name="😴 Detection",
                                value="Undetected!",
                                inline=True
                            )
                        
                        footer_text = "A masterful display of stealth!"
                        if initial_tax > 0:
                            if credits_used > 0 and actual_tax > 0:
                                footer_text += f" • ₪{credits_used:,} credits used, ₪{actual_tax:,} tax paid"
                            elif credits_used > 0:
                                footer_text += f" • ₪{credits_used:,} credits covered all taxes"
                            else:
                                footer_text += f" • Paid ₪{actual_tax:,} in taxes"
                        embed.set_footer(text=footer_text)
                        
                        await interaction.followup.send(embed=embed)
                        
                        # Set cooldown
                        self.set_cooldown(looter.id)
                        
                        if initial_tax > 0:
                            logging.info(f"{looter.display_name} stealthily looted ₪{target_cash} from {target.display_name}, used ₪{credits_used} credits, paid ₪{actual_tax} in taxes")
                        else:
                            logging.info(f"{looter.display_name} stealthily looted ₪{target_cash} from {target.display_name}")
                        
                    except Exception as e:
                        logging.error(f"❌ Failed to transfer looted money: {e}")
                        await interaction.followup.send("❌ Failed to complete the looting. Please try again.", ephemeral=True)
                
                else:
                    # Failed stealth - caught in the act, initiate combat
                    embed = discord.Embed(
                        title="🚨 Caught Red-Handed!",
                        description=f"**{looter.display_name}** was caught trying to loot **{target.display_name}**!",
                        color=0xff0000
                    )
                    
                    stealth_desc = f"🎲 **Stealth Check:** {stealth_result['stealth_roll']} + {stealth_result['dex_modifier']} = {stealth_result['stealth_total']}"
                    stealth_desc += f"\n🔍 **vs Perception:** {stealth_result['passive_perception']}"
                    
                    embed.add_field(
                        name="🎯 Failed Stealth",
                        value=stealth_desc,
                        inline=False
                    )
                    
                    embed.add_field(
                        name="⚔️ Combat Initiated",
                        value=f"**{target.display_name}** has 6 seconds to react or will automatically attack!",
                        inline=False
                    )
                    
                    embed.set_footer(text="The victim has caught you in the act!")
                    
                    await interaction.followup.send(embed=embed)
                    
                    # Set cooldown for looter
                    self.set_cooldown(looter.id)
                    
                    # Create combat with target as the "attacker" (they get first action)
                    combat_id = f"{target.id}_{looter.id}_{int(datetime.now().timestamp())}"
                    combat_data = {
                        'combat_id': combat_id,
                        'player1_id': target.id,  # Target gets first turn since they caught the looter
                        'player2_id': looter.id,
                        'current_turn': target.id,
                        'channel_id': interaction.channel.id,
                        'round': 1
                    }
                    
                    self.active_combats[combat_id] = combat_data
                    
                    # Start target's turn immediately
                    await self.start_turn(target.id, combat_data, interaction.channel)
                    
                    logging.info(f"{looter.display_name} failed to loot {target.display_name} and triggered combat")
        
        except ImportError:
            await interaction.followup.send("❌ Economy system not available.", ephemeral=True)
        except Exception as e:
            logging.error(f"❌ Error during looting: {e}")
            await interaction.followup.send("❌ An error occurred during looting. Please try again.", ephemeral=True)

    @app_commands.command(name="combat_status", description="Check your current combat status")
    @app_commands.guilds(GUILD)
    async def combat_status(self, interaction: discord.Interaction):
        """Check combat status and cooldowns"""
        user_id = interaction.user.id
        
        embed = discord.Embed(
            title="⚔️ Combat Status",
            color=0x0099ff
        )
        
        # Check if in combat
        combat_id, combat_data = self.get_combat_by_user(user_id)
        if combat_data:
            opponent_id = self.get_opponent_id(combat_data, user_id)
            opponent = self.bot.get_user(opponent_id)
            
            is_current_turn = combat_data['current_turn'] == user_id
            turn_status = "🎯 Your turn!" if is_current_turn else "⏳ Waiting for opponent"
            
            embed.add_field(
                name="🥊 Active Combat",
                value=f"Fighting **{opponent.display_name}**\nRound: {combat_data['round']}\nStatus: {turn_status}",
                inline=False
            )
            
            # Show turn timeout if it's user's turn
            if user_id in self.pending_turns:
                remaining_time = self.pending_turns[user_id]['timeout'] - datetime.now()
                remaining_seconds = max(0, remaining_time.total_seconds())
                embed.add_field(
                    name="⏰ Turn Timer",
                    value=f"{remaining_seconds:.1f} seconds remaining",
                    inline=True
                )
        else:
            embed.add_field(
                name="🕊️ Status",
                value="Not in combat",
                inline=False
            )
        
        # Check cooldown
        if self.is_on_cooldown(user_id):
            remaining = self.get_cooldown_remaining(user_id)
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
        stats_core = self.get_stats_core()
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
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCombat(bot))
    logging.info("✅ Stats Combat cog loaded successfully")