import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import logging
from datetime import datetime, timedelta
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


class StatsCombatCore(commands.Cog):
    """Core D&D-style combat mechanics and calculations"""
    
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
    
    def init_database(self):
        """Initialize database tables for combat system"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Combat log table for tracking fights
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS combat_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    attacker_id INTEGER,
                    defender_id INTEGER,
                    damage INTEGER,
                    hit BOOLEAN,
                    critical_hit BOOLEAN,
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
    
    def get_stabilization_system(self):
        """Get the stabilization system cog if available"""
        return self.bot.get_cog('StatsStabilization')
    
    def is_user_in_hospital(self, user_id):
        """Check if user is in hospital (placeholder for hospital integration)"""
        # This would integrate with your hospital system
        # For now, return False as a placeholder
        return False
    
    def get_ability_modifier(self, ability_score):
        """Calculate D&D ability modifier from ability score"""
        return (ability_score - 10) // 2
    
    def make_attack_roll(self, attacker_stats, defender_stats):
        """Make an attack roll using D&D 5e mechanics"""
        # Roll 1d20
        roll = random.randint(1, 20)
        
        # Calculate attack bonus (strength modifier + proficiency)
        str_modifier = self.get_ability_modifier(attacker_stats['strength'])
        level = attacker_stats.get('level', 1)
        proficiency_bonus = 2 + ((level - 1) // 4)  # D&D proficiency progression
        attack_bonus = str_modifier + proficiency_bonus
        
        # Calculate total attack
        total_attack = roll + attack_bonus
        
        # Calculate target AC (10 + dex modifier + natural armor based on level)
        dex_modifier = self.get_ability_modifier(defender_stats['dexterity'])
        defender_level = defender_stats.get('level', 1)
        natural_armor = (defender_level - 1) // 4  # +1 AC every 4 levels
        target_ac = 10 + dex_modifier + natural_armor
        
        # Determine hit/miss/critical
        critical_hit = (roll == 20)
        critical_miss = (roll == 1)
        hit = (total_attack >= target_ac) and not critical_miss
        
        # Critical hits always hit
        if critical_hit:
            hit = True
        
        return {
            'roll': roll,
            'attack_bonus': attack_bonus,
            'total': total_attack,
            'target_ac': target_ac,
            'hit': hit,
            'critical_hit': critical_hit,
            'critical_miss': critical_miss
        }
    
    def calculate_damage(self, attacker_stats):
        """Calculate damage for a successful hit"""
        # Base damage: 1d6 + strength modifier
        base_damage = random.randint(1, 6)
        str_modifier = self.get_ability_modifier(attacker_stats['strength'])
        
        # Level-based damage bonus
        level = attacker_stats.get('level', 1)
        level_bonus = (level - 1) // 2  # +1 damage every 2 levels
        
        total_damage = base_damage + str_modifier + level_bonus
        return max(1, total_damage)  # Minimum 1 damage
    
    def apply_damage(self, user_id, damage):
        """Apply damage to a user and return new health"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Get current health
            cursor.execute('SELECT health FROM user_stats WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                return None
            
            current_health = result[0]
            new_health = current_health - damage
            
            # Update health in database
            cursor.execute('UPDATE user_stats SET health = ? WHERE user_id = ?', (new_health, user_id))
            conn.commit()
            conn.close()
            
            return new_health
            
        except Exception as e:
            logging.error(f"❌ Failed to apply damage: {e}")
            return None
    
    def log_combat_action(self, attacker_id, defender_id, damage, hit, critical_hit):
        """Log combat action to database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO combat_log (attacker_id, defender_id, damage, hit, critical_hit)
                VALUES (?, ?, ?, ?, ?)
            ''', (attacker_id, defender_id, damage, hit, critical_hit))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"❌ Failed to log combat action: {e}")

async def setup(bot):
    await bot.add_cog(StatsCombatCore(bot))
    logging.info("✅ Stats Combat Core cog loaded successfully")