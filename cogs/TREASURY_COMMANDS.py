import discord
import logging
from discord import app_commands
from discord.ext import commands
from SHEKELS.TREASURY import get_all_treasury_balances, update_treasury_balance, get_treasury_balance

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class TreasuryCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="treasury", description="View treasury balances")
    @app_commands.guilds(GUILD)
    async def treasury(self, interaction: discord.Interaction):
        """View all treasury balances"""
        logging.info(f'Treasury command activated by {interaction.user} in #{interaction.channel}.')
        
        balances = get_all_treasury_balances()
        
        embed = discord.Embed(
            title="🏛️ Treasury Status",
            color=discord.Color.gold(),
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=f'{interaction.user} used /treasury.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        embed.add_field(
            name="🏦 Main Treasury", 
            value=f"₪{balances['treasury']:,}", 
            inline=True
        )
        embed.add_field(
            name="⛪ Church Treasury", 
            value=f"₪{balances['church']:,}", 
            inline=True
        )
        
        total = balances['treasury'] + balances['church'] + balances['kangaroo']
        embed.add_field(
            name="💰 Total Treasury Holdings", 
            value=f"₪{total:,}", 
            inline=False
        )
        
        embed.set_footer(
            text="These funds are managed by the bot",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        await interaction.response.send_message(embed=embed)
        logging.info(f'Treasury command complete.')

    @app_commands.command(name="treasury_admin", description="[ADMIN] Manage treasury balances")
    @app_commands.describe(
        treasury="Which treasury to modify",
        amount="Amount to add/subtract (negative to subtract)",
        reason="Reason for the change"
    )
    @app_commands.choices(treasury=[
        app_commands.Choice(name="Main Treasury", value="TREASURY"),
        app_commands.Choice(name="Church Treasury", value="CHURCH"),
        app_commands.Choice(name="Kangaroo Fund", value="KANGAROO")
    ])
    @app_commands.guilds(GUILD)
    async def treasury_admin(self, interaction: discord.Interaction, treasury: str, amount: int, reason: str = "Admin adjustment"):
        """Admin command to manage treasury balances"""
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ You need Administrator permissions to use this command.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        try:
            old_balance = get_treasury_balance(treasury)
            new_balance = update_treasury_balance(treasury, amount)
            
            treasury_names = {
                "TREASURY": "Main Treasury",
                "CHURCH": "Church Treasury", 
                "KANGAROO": "Kangaroo Fund"
            }
            
            embed = discord.Embed(
                title="✅ Treasury Updated",
                color=discord.Color.green(),
                timestamp=interaction.created_at
            )
            
            embed.add_field(name="Treasury", value=treasury_names[treasury], inline=True)
            embed.add_field(name="Change", value=f"₪{amount:,}", inline=True)
            embed.add_field(name="New Balance", value=f"₪{new_balance:,}", inline=True)
            embed.add_field(name="Previous Balance", value=f"₪{old_balance:,}", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            embed.set_author(
                name=f"Updated by {interaction.user}",
                icon_url=interaction.user.avatar.url if interaction.user.avatar else None
            )
            
            await interaction.followup.send(embed=embed)
            
            # Log the change
            logging.info(f"Treasury {treasury} updated by {interaction.user}: {old_balance} -> {new_balance} (change: {amount}) - Reason: {reason}")
            
        except Exception as e:
            logging.error(f"❌ Error in treasury_admin command: {e}")
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(TreasuryCommands(bot))