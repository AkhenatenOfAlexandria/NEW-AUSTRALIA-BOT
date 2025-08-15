import discord
from discord.ext import commands
from discord import app_commands
import logging

from UTILS.CONFIGURATION import GUILD_ID
from .HOSPITAL.HEALING_SERVICE import HealingService
from .HOSPITAL.HEALING_CALCULATOR import HealingCalculator
from .HOSPITAL.HEALING_LOGGER import HealingLogger

GUILD = discord.Object(id=GUILD_ID)

class HealingSystem(commands.Cog):
    """Main healing system cog - handles Discord commands"""
    
    def __init__(self, bot):
        self.bot = bot
        self.service = HealingService(bot)
        self.calculator = HealingCalculator()
        self.logger = HealingLogger(bot)
    
    @app_commands.command(name="heal", description="Restore health by paying shekels")
    async def heal(self, interaction: discord.Interaction, amount: int = None):
        """Delegate to healing service"""
        await self.service.process_healing_request(interaction, amount)
    
    @app_commands.command(name="healing_cost", description="Check the cost to heal yourself")
    async def healing_cost(self, interaction: discord.Interaction, amount: int = None):
        """Delegate to cost calculator"""
        await self.calculator.show_healing_cost(interaction, amount)
    
    @app_commands.command(name="infirmary", description="View infirmary information")
    async def infirmary(self, interaction: discord.Interaction):
        """Show infirmary information"""
        await self.service.show_infirmary_info(interaction)