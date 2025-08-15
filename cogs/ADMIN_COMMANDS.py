import discord
import logging
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import json
import os

from SHEKELS.BALANCE import BALANCE
from SHEKELS.TRANSFERS import ADD_MONEY
from SHEKELS.TAX import WEALTH_TAX
from SHEKELS.GAMES.STOCK_MARKET import STOCK_CHANGE
from UTILS.FUNCTIONS import is_role, BALANCE_UPDATED, USER_FINDER
from UTILS.CONFIGURATION import MONEY_LOG_ID, ANNOUNCEMENTS_ID

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.warnings_file = "warnings.json"
        self.load_warnings()

    def load_warnings(self):
        """Load warnings from file"""
        try:
            if os.path.exists(self.warnings_file):
                with open(self.warnings_file, 'r') as f:
                    self.warnings = json.load(f)
            else:
                self.warnings = {}
        except Exception as e:
            logging.error(f"Error loading warnings: {e}")
            self.warnings = {}

    def save_warnings(self):
        """Save warnings to file"""
        try:
            with open(self.warnings_file, 'w') as f:
                json.dump(self.warnings, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving warnings: {e}")

    def get_user_warnings(self, user_id: str):
        """Get warnings for a specific user"""
        return self.warnings.get(user_id, [])

    def add_warning(self, user_id: str, moderator_id: str, reason: str, timestamp: str):
        """Add a warning for a user"""
        if user_id not in self.warnings:
            self.warnings[user_id] = []
        
        warning = {
            "id": len(self.warnings[user_id]) + 1,
            "reason": reason,
            "moderator_id": moderator_id,
            "timestamp": timestamp
        }
        
        self.warnings[user_id].append(warning)
        self.save_warnings()
        return warning["id"]

    def remove_warning(self, user_id: str, warning_id: int):
        """Remove a specific warning"""
        if user_id not in self.warnings:
            return False
        
        user_warnings = self.warnings[user_id]
        for i, warning in enumerate(user_warnings):
            if warning["id"] == warning_id:
                user_warnings.pop(i)
                if not user_warnings:  # Remove user entry if no warnings left
                    del self.warnings[user_id]
                self.save_warnings()
                return True
        return False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has Administrator role for all commands in this cog"""
        if not any(role.name == "Administrator" for role in interaction.user.roles):
            await interaction.response.send_message("You need the Administrator role to use this command.", ephemeral=True)
            return False
        return True

    @app_commands.command(name="add_money", description="[ADMIN] Add or remove money from a user")
    @app_commands.describe(
        user="User to modify balance for",
        amount="Amount to add (negative to remove)",
        balance_type="Whether to modify cash or bank balance"
    )
    @app_commands.choices(balance_type=[
        app_commands.Choice(name="Cash", value="CASH"),
        app_commands.Choice(name="Bank", value="BANK")
    ])
    @app_commands.guilds(GUILD)
    async def money(self, interaction: discord.Interaction, user: discord.Member, amount: int, balance_type: str = "BANK"):
        BALANCE(user)
        ADD_MONEY(user, amount, interaction.created_at, balance_type)
        
        _BANK = amount if balance_type == "BANK" else 0
        _CASH = amount if balance_type == "CASH" else 0
        STRING = "Bank" if balance_type == "BANK" else "Cash"
        
        if amount > 0:
            ADD = ("Added", "to")
            display_amount = amount
        else:
            ADD = ("Removed", "from")
            display_amount = -amount
            
        await interaction.response.send_message(f"{ADD[0]} ₪{display_amount} {ADD[1]} {user.mention}'s {STRING} balance.")
        
        MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
        if MONEY_LOG:
            EMBED = BALANCE_UPDATED(
                TIME=interaction.created_at,
                USER=user,
                REASON="MONEY",
                CASH=_CASH,
                BANK=_BANK,
                MESSAGE=None
            )
            await MONEY_LOG.send(embed=EMBED)

    @app_commands.command(name="role_money", description="[ADMIN] Add or remove money from all users with a role")
    @app_commands.describe(
        role="Role to modify balance for",
        amount="Amount to add (negative to remove)",
        balance_type="Whether to modify cash or bank balance"
    )
    @app_commands.choices(balance_type=[
        app_commands.Choice(name="Cash", value="CASH"),
        app_commands.Choice(name="Bank", value="BANK")
    ])
    @app_commands.guilds(GUILD)
    async def role_money(self, interaction: discord.Interaction, role: discord.Role, amount: int, balance_type: str = "BANK"):
        await interaction.response.defer()  # This might take a while
        
        ROLE_MEMBERS = role.members
        
        for MEMBER in ROLE_MEMBERS:
            logging.debug(f"Attempting to modify money for {MEMBER}.")
            BALANCE(MEMBER)
            ADD_MONEY(MEMBER, amount, interaction.created_at, balance_type)
            
            _BANK = amount if balance_type == "BANK" else 0
            _CASH = amount if balance_type == "CASH" else 0
            
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=MEMBER,
                    REASON="MONEY",
                    CASH=_CASH,
                    BANK=_BANK,
                    MESSAGE=None
                )
                await MONEY_LOG.send(embed=EMBED)
        
        if amount > 0:
            ADD = ("Added", "to")
            display_amount = amount
        else:
            ADD = ("Removed", "from")
            display_amount = -amount
            
        NUMBER = len(ROLE_MEMBERS)
        await interaction.followup.send(f"{ADD[0]} ₪{display_amount} {ADD[1]} {balance_type} balance of {NUMBER} Members with role {role.name}.")

    @app_commands.command(name="stockupdate", description="[ADMIN] Manually update stock prices")
    @app_commands.guilds(GUILD)
    async def stockupdate(self, interaction: discord.Interaction):
        STOCK_CHANGE()
        STRING = "Stock Prices have been updated. Use /stockmarket to view them."
        await interaction.response.send_message(STRING)

    @app_commands.command(name="wealthtax", description="[ADMIN] Manually collect wealth tax")
    @app_commands.guilds(GUILD)
    async def wealthtax(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        tax_result = WEALTH_TAX()
        ANNOUNCEMENTS = self.bot.get_channel(ANNOUNCEMENTS_ID)
        if ANNOUNCEMENTS:
            await ANNOUNCEMENTS.send(f"Wealth Tax collected:\n{tax_result}")
            await interaction.followup.send("Wealth tax collected and announced.")
        else:
            await interaction.followup.send(f"Wealth Tax collected:\n{tax_result}")
            logging.error("ANNOUNCEMENTS CHANNEL NOT FOUND.")

    @app_commands.command(name="warn", description="[ADMIN] Issue a warning to a user")
    @app_commands.describe(
        user="User to warn",
        reason="Reason for the warning"
    )
    @app_commands.guilds(GUILD)
    async def warn(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        logging.info(f'Warn activated by {interaction.user} for {user}.')
        
        user_id = str(user.id)
        moderator_id = str(interaction.user.id)
        timestamp = interaction.created_at.isoformat()
        
        warning_id = self.add_warning(user_id, moderator_id, reason, timestamp)
        user_warnings = self.get_user_warnings(user_id)
        warning_count = len(user_warnings)
        
        # Create warning embed
        EMBED = discord.Embed(
            colour=discord.Colour.orange(),
            title="⚠️ User Warned",
            description=f"**User:** {user.mention}\n**Reason:** {reason}\n**Warning #{warning_count}**",
            timestamp=interaction.created_at
        )
        EMBED.set_author(
            name=f"Warned by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_footer(
            text=f"Warning ID: {warning_id}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        await interaction.response.send_message(embed=EMBED)
        
        # Try to DM the user
        try:
            dm_embed = discord.Embed(
                colour=discord.Colour.orange(),
                title="⚠️ Warning Received",
                description=f"You have received a warning in **{interaction.guild.name}**\n\n**Reason:** {reason}\n**Warning #{warning_count}**",
                timestamp=interaction.created_at
            )
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ Could not DM {user.mention} about the warning.", ephemeral=True)
        
        logging.info(f'Warning #{warning_id} issued to {user} by {interaction.user}: {reason}')

    @app_commands.command(name="warnings", description="[ADMIN] View warnings for a user")
    @app_commands.describe(user="User to check warnings for")
    @app_commands.guilds(GUILD)
    async def warnings(self, interaction: discord.Interaction, user: discord.Member):
        user_id = str(user.id)
        user_warnings = self.get_user_warnings(user_id)
        
        if not user_warnings:
            EMBED = discord.Embed(
                colour=discord.Colour.green(),
                title="✅ No Warnings",
                description=f"{user.mention} has no warnings.",
                timestamp=interaction.created_at
            )
        else:
            warning_text = ""
            for warning in user_warnings[-10:]:  # Show last 10 warnings
                moderator = self.bot.get_user(int(warning["moderator_id"]))
                mod_name = moderator.mention if moderator else f"Unknown (ID: {warning['moderator_id']})"
                
                # Parse timestamp
                try:
                    warn_time = datetime.fromisoformat(warning["timestamp"])
                    time_str = warn_time.strftime("%Y-%m-%d %H:%M")
                except:
                    time_str = "Unknown time"
                
                warning_text += f"**#{warning['id']}** - {warning['reason']}\n"
                warning_text += f"*By {mod_name} on {time_str}*\n\n"
            
            EMBED = discord.Embed(
                colour=discord.Colour.red(),
                title=f"⚠️ Warnings for {user.display_name}",
                description=warning_text,
                timestamp=interaction.created_at
            )
            EMBED.set_footer(text=f"Total warnings: {len(user_warnings)} | Showing most recent 10")
        
        EMBED.set_author(
            name=f"Requested by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        await interaction.response.send_message(embed=EMBED)

    @app_commands.command(name="unwarn", description="[ADMIN] Remove a specific warning from a user")
    @app_commands.describe(
        user="User to remove warning from",
        warning_id="ID of the warning to remove"
    )
    @app_commands.guilds(GUILD)
    async def unwarn(self, interaction: discord.Interaction, user: discord.Member, warning_id: int):
        user_id = str(user.id)
        
        if self.remove_warning(user_id, warning_id):
            EMBED = discord.Embed(
                colour=discord.Colour.green(),
                title="✅ Warning Removed",
                description=f"Warning #{warning_id} has been removed from {user.mention}.",
                timestamp=interaction.created_at
            )
            EMBED.set_author(
                name=f"Removed by {interaction.user}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.response.send_message(embed=EMBED)
            logging.info(f'Warning #{warning_id} removed from {user} by {interaction.user}')
        else:
            await interaction.response.send_message(f"❌ Warning #{warning_id} not found for {user.mention}.", ephemeral=True)

    @app_commands.command(name="clearwarnings", description="[ADMIN] Clear all warnings for a user")
    @app_commands.describe(user="User to clear warnings for")
    @app_commands.guilds(GUILD)
    async def clearwarnings(self, interaction: discord.Interaction, user: discord.Member):
        user_id = str(user.id)
        user_warnings = self.get_user_warnings(user_id)
        
        if not user_warnings:
            await interaction.response.send_message(f"{user.mention} has no warnings to clear.", ephemeral=True)
            return
        
        warning_count = len(user_warnings)
        
        # Clear all warnings for the user
        if user_id in self.warnings:
            del self.warnings[user_id]
            self.save_warnings()
        
        EMBED = discord.Embed(
            colour=discord.Colour.green(),
            title="✅ Warnings Cleared",
            description=f"All {warning_count} warning(s) have been cleared for {user.mention}.",
            timestamp=interaction.created_at
        )
        EMBED.set_author(
            name=f"Cleared by {interaction.user}",
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        
        await interaction.response.send_message(embed=EMBED)
        logging.info(f'All {warning_count} warnings cleared for {user} by {interaction.user}')

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))