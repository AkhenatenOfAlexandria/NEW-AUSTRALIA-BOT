import discord
import logging
from discord import app_commands
from discord.ext import commands

from SHEKELS.GAMES.STOCK_MARKET import VIEW_STOCKS, BUY_STOCK, SELL_STOCK
from FUNCTIONS import BALANCE_UPDATED
from UTILS.CONFIGURATION import MONEY_LOG_ID

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class StockCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="stockmarket", description="View current stock prices")
    @app_commands.guilds(GUILD)
    async def stockmarket(self, interaction: discord.Interaction):
        EMBED = VIEW_STOCKS()
        EMBED.timestamp = interaction.created_at
        EMBED.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        EMBED.set_author(
            name=f'{interaction.user} used /stockmarket.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=EMBED)

    @app_commands.command(name="buy_stock", description="Buy stocks")
    @app_commands.describe(
        stock="Stock symbol to buy",
        amount="Number of shares to buy (default: 1)"
    )
    @app_commands.guilds(GUILD)
    async def buy_stock(self, interaction: discord.Interaction, stock: str, amount: int = 1):
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
            
        try:
            PRICE = BUY_STOCK(interaction.user, stock.upper())
            total_price = PRICE * amount
            
            await interaction.response.send_message(f"Bought {amount} {stock.upper()} for ₪{total_price}.")
            
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=interaction.user,
                    REASON="STOCK BUY",
                    CASH=-total_price,
                    MESSAGE=None
                )
                await MONEY_LOG.send(embed=EMBED)
        except KeyError as e:
            await interaction.response.send_message(f"Stock not found: {e}", ephemeral=True)
            logging.error(f"KeyError: {e}")
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            logging.error(f"ValueError: {e}")

    @app_commands.command(name="sell_stock", description="Sell stocks")
    @app_commands.describe(stock="Stock symbol to sell")
    @app_commands.guilds(GUILD)
    async def sell_stock(self, interaction: discord.Interaction, stock: str):
        try:
            RETURN = SELL_STOCK(interaction.user, stock.upper())
            await interaction.response.send_message(RETURN[0])
            
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=interaction.user,
                    REASON="STOCK SELL",
                    CASH=RETURN[2]-RETURN[1],
                    MESSAGE=None
                )
                await MONEY_LOG.send(embed=EMBED)
        except KeyError as e:
            await interaction.response.send_message(f"Stock not found: {e}", ephemeral=True)
            logging.error(f"KeyError: {e}")

async def setup(bot):
    await bot.add_cog(StockCommands(bot))