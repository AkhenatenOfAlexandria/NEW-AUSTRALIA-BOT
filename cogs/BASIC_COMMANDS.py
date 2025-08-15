import discord
import logging
import random

from discord import app_commands
from discord.ext import commands
from datetime import datetime

from UTILS.CONFIGURATION import GUILD_ID
from ASK import REPLY
from BIBLE.BIBLE import BIBLE
from SHEKELS.BALANCE import BALANCE

GUILD = discord.Object(id=GUILD_ID)

class BasicCommands(commands.Cog):
    
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ask", description="Ask the Glorious Leader a question")
    @app_commands.describe(question="The question you want to ask")
    @app_commands.guilds(GUILD)
    async def ask(self, interaction: discord.Interaction, question: str):
        logging.info(f'Ask activated by {interaction.user} in #{interaction.channel}.')
        
        RESPONSE, ANSWER = REPLY()
        if ANSWER == "Y":
            COLOUR = discord.Colour.green()
        elif ANSWER == "N":
            COLOUR = discord.Colour.red()
        else:
            COLOUR = discord.Colour.blue()
            
        EMBED = discord.Embed(
            colour=COLOUR,
            title="Thus saith the Glorious Leader:",
            description=RESPONSE,
            timestamp=interaction.created_at
        )
        EMBED.set_author(
            name=f'{interaction.user} asked: "{question}"',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_thumbnail(url="https://i.kym-cdn.com/entries/icons/original/000/011/464/tumblr_m2shy4dIV61ru44ono1_500.jpg")
        EMBED.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=EMBED)
        logging.info(f'Ask complete: "{RESPONSE}"')

    @app_commands.command(name="bible", description="Get a Bible verse")
    @app_commands.describe(reference="Bible verse reference (e.g., John 3:16)")
    @app_commands.guilds(GUILD)
    async def bible(self, interaction: discord.Interaction, reference: str):
        try:
            EMBED = BIBLE(reference)
            await interaction.response.send_message(embed=EMBED)
        except Exception as e:
            await interaction.response.send_message(f"Error: {e}", ephemeral=True)

    @app_commands.command(name="echo", description="Echo back a message")
    @app_commands.describe(message="The message to echo back")
    @app_commands.guilds(GUILD)
    async def echo(self, interaction: discord.Interaction, message: str):
        logging.info(f'Echo activated by {interaction.user} in #{interaction.channel}.')
        await interaction.response.send_message(message)
        logging.info("Echo complete.")

    @app_commands.command(name="ping", description="Check bot latency")
    @app_commands.guilds(GUILD)
    async def ping(self, interaction: discord.Interaction):
        bot_ping = round(self.bot.latency * 1000)
        STRING = f'{bot_ping} milliseconds'
        
        EMBED = discord.Embed(
            colour=discord.Colour.blue(),
            description=STRING,
            title="Pong!",
            timestamp=interaction.created_at
        )
        EMBED.set_author(
            name=f'{interaction.user} used /ping.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=EMBED)

    @app_commands.command(name="avatar", description="Displays your avatar or someone else's avatar")
    @app_commands.describe(user="The user whose avatar you want to see (optional)")
    @app_commands.guilds(GUILD)
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        logging.info(f'Avatar activated by {interaction.user} in #{interaction.channel}.')
        
        # If no user specified, use the person who ran the command
        target_user = user if user else interaction.user
        
        # Get the avatar URL (with fallback to default avatar)
        avatar_url = target_user.avatar.url if target_user.avatar else target_user.default_avatar.url
        
        EMBED = discord.Embed(
            colour=discord.Colour.blue(),
            title=f"{target_user.display_name}'s Avatar",
            timestamp=interaction.created_at
        )
        EMBED.set_image(url=avatar_url)
        EMBED.set_author(
            name=f'{interaction.user} requested avatar.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=EMBED)
        logging.info(f'Avatar complete: showed {target_user.display_name}\'s avatar')

    @app_commands.command(name="roll", description="Roll dice (e.g., 2d6, 1d20, 3d8)")
    @app_commands.describe(dice="Dice notation (e.g., 2d6 for two 6-sided dice)")
    @app_commands.guilds(GUILD)
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        logging.info(f'Roll activated by {interaction.user} in #{interaction.channel}.')
        
        try:
            # Parse dice notation (e.g., "2d6" -> 2 dice with 6 sides each)
            if 'd' not in dice.lower():
                raise ValueError("Invalid dice notation")
            
            parts = dice.lower().split('d')
            if len(parts) != 2:
                raise ValueError("Invalid dice notation")
            
            num_dice = int(parts[0]) if parts[0] else 1
            num_sides = int(parts[1])
            
            # Validate input
            if num_dice < 1 or num_dice > 20:
                raise ValueError("Number of dice must be between 1 and 20")
            if num_sides < 2 or num_sides > 1000:
                raise ValueError("Number of sides must be between 2 and 1000")
            
            # Roll the dice
            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Format the results
            if num_dice == 1:
                result_text = f"🎲 **{total}**"
            else:
                rolls_text = " + ".join(map(str, rolls))
                result_text = f"🎲 [{rolls_text}] = **{total}**"
            
            EMBED = discord.Embed(
                colour=discord.Colour.gold(),
                title=f"Rolling {dice}",
                description=result_text,
                timestamp=interaction.created_at
            )
            EMBED.set_author(
                name=f'{interaction.user} rolled dice.',
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            EMBED.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
            
            await interaction.response.send_message(embed=EMBED)
            logging.info(f'Roll complete: {dice} -> {rolls} (total: {total})')
            
        except ValueError as e:
            error_msg = "Invalid dice notation! Use format like: 1d6, 2d20, 3d8"
            if "between" in str(e):
                error_msg = str(e)
            await interaction.response.send_message(f"❌ {error_msg}", ephemeral=True)
            logging.warning(f'Roll failed: {e}')
        except Exception as e:
            await interaction.response.send_message("❌ An error occurred while rolling dice.", ephemeral=True)
            logging.error(f'Roll error: {e}')

    @app_commands.command(name="serverinfo", description="Display server information")
    @app_commands.guilds(GUILD)  # Added missing guilds decorator
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"📊 {guild.name} Server Information",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="👑 Supreme Kangaroo Lord (glory be to Him)", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
        embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        
        embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
        embed.add_field(name="📝 Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        
        embed.add_field(name="🔒 Verification Level", value=str(guild.verification_level).title(), inline=True)
        embed.add_field(name="💬 Text Channels", value=len(guild.text_channels), inline=True)
        embed.add_field(name="🔊 Voice Channels", value=len(guild.voice_channels), inline=True)
        
        if guild.description:
            embed.add_field(name="📄 Description", value=guild.description, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="userinfo", description="Display comprehensive information about a user including balance")
    @app_commands.describe(member="The member to get information about")
    @app_commands.guilds(GUILD)
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        if member is None:
            member = interaction.user
        
        # Get balance information
        try:
            _BALANCE = BALANCE(member)
            balance_available = True
        except Exception as e:
            logging.warning(f"Could not get balance for {member}: {e}")
            balance_available = False
        
        embed = discord.Embed(
            title=f"👤 {member} User Information",
            color=member.color if member.color != discord.Color.default() else discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.set_author(
            name=f'{interaction.user} used /userinfo.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        embed.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Basic user information
        embed.add_field(name="🆔 User ID", value=member.id, inline=True)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(member.created_at.timestamp())}:D>", inline=True)
        
        # Handle potential None value for joined_at
        if member.joined_at:
            embed.add_field(name="📥 Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:D>", inline=True)
        else:
            embed.add_field(name="📥 Joined Server", value="Unknown", inline=True)
        
        # Balance information (if available)
        if balance_available:
            embed.add_field(name="💰 Cash", value=f"₪{_BALANCE[0]}", inline=True)
            embed.add_field(name="🏦 Bank", value=f"₪{_BALANCE[1]}", inline=True)
            embed.add_field(name="💎 Total Balance", value=f"₪{_BALANCE[2]}", inline=True)
            embed.add_field(name="📊 Credit", value=f"{_BALANCE[3]*100}%", inline=True)
        else:
            embed.add_field(name="💰 Balance", value="Unavailable", inline=True)
        
        # Role and server information
        embed.add_field(name="🏆 Highest Role", value=member.top_role.mention, inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if member.bot else "No", inline=True)
        
        if member.premium_since:
            embed.add_field(name="💎 Nitro Boosting Since", value=f"<t:{int(member.premium_since.timestamp())}:D>", inline=True)
        
        # Show roles (limit to prevent embed being too long)
        roles = [role.mention for role in member.roles[1:]]  # Exclude @everyone
        if roles:
            roles_text = ", ".join(roles[:8])  # Reduced to 8 roles to make room for balance info
            if len(member.roles) > 9:
                roles_text += f" and {len(member.roles) - 9} more..."
            embed.add_field(name="🎭 Roles", value=roles_text, inline=False)
        
        await interaction.response.send_message(embed=embed)
        logging.info(f'Combined userinfo complete for {member}')

        
async def setup(bot):
    await bot.add_cog(BasicCommands(bot))