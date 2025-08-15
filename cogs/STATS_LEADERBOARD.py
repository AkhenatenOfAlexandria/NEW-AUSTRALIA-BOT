import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import logging

from UTILS.CONFIGURATION import GUILD_ID
GUILD = discord.Object(id=GUILD_ID)


class StatsLeaderboards(commands.Cog):
    """Leaderboards and ranking system for character stats"""
    
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="stats_leaderboard", description="View stats leaderboard")
    @app_commands.describe(stat="Which stat to sort by")
    @app_commands.choices(stat=[
        app_commands.Choice(name="Level", value="level"),
        app_commands.Choice(name="Health", value="health"),
        app_commands.Choice(name="Strength", value="strength"),
        app_commands.Choice(name="Dexterity", value="dexterity"),
        app_commands.Choice(name="Constitution", value="constitution"),
        app_commands.Choice(name="Intelligence", value="intelligence"),
        app_commands.Choice(name="Wisdom", value="wisdom"),
        app_commands.Choice(name="Charisma", value="charisma")
    ])
    @app_commands.guilds(GUILD)
    async def stats_leaderboard(self, interaction: discord.Interaction, stat: str = "level"):
        """View a leaderboard for a specific stat"""
        await interaction.response.defer()
        
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Validate stat parameter to prevent SQL injection
            valid_stats = ['level', 'health', 'strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
            if stat not in valid_stats:
                await interaction.followup.send("❌ Invalid stat parameter.")
                return
            
            # Get top 10 users for the specified stat (safe since we validated the parameter)
            query = f'''
                SELECT user_id, username, {stat} 
                FROM user_stats 
                ORDER BY {stat} DESC 
                LIMIT 10
            '''
            cursor.execute(query)
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                await interaction.followup.send("❌ No stats found in the database.")
                return
            
            # Create leaderboard embed
            embed = discord.Embed(
                title=f"🏆 {stat.title()} Leaderboard",
                color=0xffd700
            )
            
            stat_emojis = {
                'level': '🌟',
                'health': '❤️',
                'strength': '💪',
                'dexterity': '🏃', 
                'constitution': '🛡️',
                'intelligence': '🧠',
                'wisdom': '👁️',
                'charisma': '💬'
            }
            
            leaderboard_text = ""
            for i, (user_id, username, value) in enumerate(results, 1):
                # Try to get current member to get updated display name
                try:
                    member = interaction.guild.get_member(user_id)
                    display_name = member.display_name if member else username
                except:
                    display_name = username
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                if stat == "health":
                    leaderboard_text += f"{medal} **{display_name}** - {value} HP\n"
                elif stat == "level":
                    leaderboard_text += f"{medal} **{display_name}** - Level {value}\n"
                else:
                    leaderboard_text += f"{medal} **{display_name}** - {value}\n"
            
            embed.description = leaderboard_text
            embed.set_footer(text="Use /stats to view your complete character sheet")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Error in stats_leaderboard command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="my_ranking", description="See your ranking in all stats")
    @app_commands.guilds(GUILD)
    async def my_ranking(self, interaction: discord.Interaction):
        """Show the user's ranking across all stats"""
        await interaction.response.defer()
        
        try:
            stats_core = self.bot.get_cog('StatsCore')
            if not stats_core:
                await interaction.followup.send("❌ Stats core system not available.")
                return
            
            user_stats = stats_core.get_user_stats(interaction.user.id)
            if not user_stats:
                await interaction.followup.send("❌ You don't have character stats yet! An admin can assign them using `/assign_stats`.")
                return
            
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            embed = discord.Embed(
                title=f"📊 {interaction.user.display_name}'s Rankings",
                color=0x00ff00
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Get rankings for each stat
            stats_to_check = ['level', 'health', 'strength', 'dexterity', 'constitution', 'intelligence', 'wisdom', 'charisma']
            stat_emojis = {
                'level': '🌟',
                'health': '❤️',
                'strength': '💪',
                'dexterity': '🏃', 
                'constitution': '🛡️',
                'intelligence': '🧠',
                'wisdom': '👁️',
                'charisma': '💬'
            }
            
            rankings = []
            
            for stat in stats_to_check:
                # Count how many users have a higher value in this stat
                cursor.execute(f'''
                    SELECT COUNT(*) + 1 as rank
                    FROM user_stats 
                    WHERE {stat} > ?
                ''', (user_stats[stat],))
                
                rank = cursor.fetchone()[0]
                
                # Get total number of users with stats
                cursor.execute('SELECT COUNT(*) FROM user_stats')
                total_users = cursor.fetchone()[0]
                
                value = user_stats[stat]
                if stat == "health":
                    value_str = f"{value} HP"
                elif stat == "level":
                    value_str = f"Level {value}"
                else:
                    value_str = str(value)
                
                rankings.append(f"{stat_emojis[stat]} **{stat.title()}**: {value_str} (#{rank}/{total_users})")
            
            conn.close()
            
            # Split rankings into two columns
            mid_point = len(rankings) // 2
            left_column = rankings[:mid_point]
            right_column = rankings[mid_point:]
            
            embed.add_field(
                name="📈 Rankings (1/2)",
                value="\n".join(left_column),
                inline=True
            )
            
            embed.add_field(
                name="📈 Rankings (2/2)",
                value="\n".join(right_column),
                inline=True
            )
            
            # Calculate overall rank (based on level)
            embed.add_field(
                name="🏆 Overall Rank",
                value=f"**#{rankings[0].split('#')[1].split('/')[0]}** out of {total_users} players",
                inline=False
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Error in my_ranking command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")
    
    @app_commands.command(name="top_players", description="View overall top players by level")
    @app_commands.guilds(GUILD)
    async def top_players(self, interaction: discord.Interaction):
        """Show the top 15 players by level with all their stats"""
        await interaction.response.defer()
        
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Get top 15 players by level
            cursor.execute('''
                SELECT user_id, username, level, health, strength, dexterity, constitution, intelligence, wisdom, charisma
                FROM user_stats 
                ORDER BY level DESC, health DESC
                LIMIT 15
            ''')
            
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                await interaction.followup.send("❌ No player data found.")
                return
            
            embed = discord.Embed(
                title="🏆 Top Players",
                description="Ranked by Level (then Health)",
                color=0xffd700
            )
            
            # Create a formatted leaderboard
            leaderboard_text = ""
            for i, (user_id, username, level, health, str_val, dex, con, int_val, wis, cha) in enumerate(results, 1):
                # Try to get current member name
                try:
                    member = interaction.guild.get_member(user_id)
                    display_name = member.display_name if member else username
                except:
                    display_name = username
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                leaderboard_text += f"{medal} **{display_name}** - Level {level} ({health} HP)\n"
                
                # Add a gap every 5 players for readability
                if i % 5 == 0 and i < 15:
                    leaderboard_text += "\n"
            
            embed.description = leaderboard_text
            embed.set_footer(text="Use /stats [player] to view detailed stats • /my_ranking to see your position")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logging.error(f"❌ Error in top_players command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(StatsLeaderboards(bot))
    logging.info("✅ Stats Leaderboards cog loaded successfully")