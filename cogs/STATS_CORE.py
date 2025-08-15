import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import random
import logging
from typing import Optional

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


# D&D 5e XP thresholds for levels 1-20 (used as default Shekel costs)
DEFAULT_LEVEL_COSTS = {
    2: 300, 3: 900, 4: 2700, 5: 6500, 6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
    11: 85000, 12: 100000, 13: 120000, 14: 140000, 15: 165000, 16: 195000, 17: 225000, 
    18: 265000, 19: 305000, 20: 355000
}

class StatsCore(commands.Cog):
    """Core stats system - handles stat generation, storage, and basic viewing"""
    
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
    
    def init_database(self):
        """Initialize the stats database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    strength INTEGER,
                    dexterity INTEGER,
                    constitution INTEGER,
                    intelligence INTEGER,
                    wisdom INTEGER,
                    charisma INTEGER,
                    health INTEGER,
                    level INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS level_costs (
                    level INTEGER PRIMARY KEY,
                    cost INTEGER NOT NULL
                )
            ''')
            
            cursor.execute('SELECT COUNT(*) FROM level_costs')
            if cursor.fetchone()[0] == 0:
                for level, cost in DEFAULT_LEVEL_COSTS.items():
                    cursor.execute('INSERT INTO level_costs (level, cost) VALUES (?, ?)', (level, cost))
            
            conn.commit()
            conn.close()
            logging.info("✅ Stats database initialized successfully")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize stats database: {e}")
    
    def get_constitution_modifier(self, constitution):
        """Calculate D&D ability modifier from ability score"""
        return (constitution - 10) // 2
    
    def calculate_health(self, constitution, level=1):
        """Calculate health using D&D mechanics"""
        base_hit_die = 8
        con_modifier = self.get_constitution_modifier(constitution)
        base_health = base_hit_die + con_modifier
        hit_die_average = 5
        additional_health = (level - 1) * (hit_die_average + con_modifier)
        total_health = base_health + additional_health
        return max(level, total_health)
    
    def generate_stats(self):
        """Generate a random set of ability scores using the standard array"""
        stats = [15, 14, 13, 12, 10, 8]
        random.shuffle(stats)
        constitution = stats[2]
        level = 1
        
        return {
            'strength': stats[0],
            'dexterity': stats[1], 
            'constitution': constitution,
            'intelligence': stats[3],
            'wisdom': stats[4],
            'charisma': stats[5],
            'level': level,
            'health': self.calculate_health(constitution, level)
        }
    
    def save_user_stats(self, user_id: int, username: str, stats: dict):
        """Save user stats to database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO user_stats 
                (user_id, username, strength, dexterity, constitution, intelligence, wisdom, charisma, health, level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, username, 
                stats['strength'], stats['dexterity'], stats['constitution'],
                stats['intelligence'], stats['wisdom'], stats['charisma'], 
                stats['health'], stats.get('level', 1)
            ))
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to save stats for {username}: {e}")
            return False
    
    def get_user_stats(self, user_id: int):
        """Get user stats from database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM user_stats WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                return {
                    'user_id': result[0],
                    'username': result[1],
                    'strength': result[2],
                    'dexterity': result[3],
                    'constitution': result[4],
                    'intelligence': result[5],
                    'wisdom': result[6],
                    'charisma': result[7],
                    'health': result[8],
                    'level': result[9],
                    'created_at': result[10]
                }
            return None
            
        except Exception as e:
            logging.error(f"❌ Failed to get stats for user {user_id}: {e}")
            return None
    
    def get_all_users_with_stats(self):
        """Get all users who have stats assigned"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM user_stats')
            results = cursor.fetchall()
            conn.close()
            return [row[0] for row in results]
        except Exception as e:
            logging.error(f"❌ Failed to get users with stats: {e}")
            return []
    
    def create_stats_embed(self, user: discord.Member, stats: dict):
        """Create a Discord embed for displaying stats"""
        embed = discord.Embed(
            title=f"📊 Level {stats.get('level', 1)} User - {user.display_name}",
            color=0x00ff00
        )
        
        embed.set_thumbnail(url=user.display_avatar.url)
        
        embed.add_field(
            name="🌟 Level", 
            value=f"**{stats.get('level', 1)}**", 
            inline=True
        )
        
        stat_emojis = {
            'strength': '💪',
            'dexterity': '🏃',
            'constitution': '🛡️',
            'intelligence': '🧠',
            'wisdom': '👁️',
            'charisma': '💬'
        }
        
        basic_stats = ['strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
        for stat in basic_stats:
            if stat in stats:
                embed.add_field(
                    name=f"{stat_emojis[stat]} {stat.title()}", 
                    value=f"**{stats[stat]}**", 
                    inline=True
                )
        
        if 'health' in stats:
            con_mod = self.get_constitution_modifier(stats.get('constitution', 10))
            con_mod_str = f"+{con_mod}" if con_mod >= 0 else str(con_mod)
            level = stats.get('level', 1)
            
            if level == 1:
                health_calc = f"*(8 {con_mod_str} CON)*"
            else:
                additional_hp = (level - 1) * (5 + con_mod)
                health_calc = f"*(8 {con_mod_str} + {additional_hp} from levels)*"
            
            embed.add_field(
                name="❤️ Health", 
                value=f"**{stats['health']}** HP\n{health_calc}", 
                inline=True
            )
        
        modifiers = []
        for stat in basic_stats:
            if stat in stats:
                modifier = self.get_constitution_modifier(stats[stat])
                mod_str = f"+{modifier}" if modifier >= 0 else str(modifier)
                modifiers.append(f"{stat.title()}: {mod_str}")
        
        embed.add_field(
            name="📈 Modifiers", 
            value="\n".join(modifiers), 
            inline=False
        )
        
        if 'created_at' in stats:
            embed.set_footer(text=f"Stats assigned on {stats['created_at']}")
        
        return embed
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Automatically assign stats when a new member joins"""
        try:
            existing_stats = self.get_user_stats(member.id)
            if existing_stats:
                logging.info(f"User {member.display_name} already has stats, skipping assignment")
                return
            
            stats = self.generate_stats()
            
            if self.save_user_stats(member.id, member.display_name, stats):
                logging.info(f"✅ Assigned stats to new member: {member.display_name}")
            
        except Exception as e:
            logging.error(f"❌ Failed to assign stats to {member.display_name}: {e}")
    
    @app_commands.command(name="stats", description="View your character stats")
    @app_commands.guilds(GUILD)
    async def view_stats(self, interaction: discord.Interaction, member: Optional[discord.Member] = None):
        """View stats for yourself or another member"""
        target = member or interaction.user
        
        stats = self.get_user_stats(target.id)
        if not stats:
            if target == interaction.user:
                await interaction.response.send_message("❌ You don't have stats yet! An admin can assign them using `/assign_stats`.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ {target.display_name} doesn't have stats yet!", ephemeral=True)
            return
        
        embed = self.create_stats_embed(target, stats)
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(StatsCore(bot))
    logging.info("✅ Stats Core cog loaded successfully")  # Correct message