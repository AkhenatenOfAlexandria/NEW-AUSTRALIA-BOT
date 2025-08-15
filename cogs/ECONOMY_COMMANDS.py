import discord
import logging
import traceback
from discord import app_commands
from discord.ext import commands

from SHEKELS.BALANCE import BALANCE, ECONOMY, VIEW_PORTFIOLIO, LEADERBOARD, ADD_TAX_CREDITS
from SHEKELS.TRANSFERS import WITHDRAW, DEPOSIT, PAY, UPDATE_BALANCE
from SHEKELS.TREASURY import update_treasury_balance
from FUNCTIONS import USER_FINDER, BALANCE_UPDATED
from UTILS.CONFIGURATION import MONEY_LOG_ID

GUILD_ID = 574731470900559872
GUILD = discord.Object(id=GUILD_ID)

class EconomyCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    def get_stats_core(self):
        """Get the StatsCore cog for accessing core functionality"""
        return self.bot.get_cog('StatsCore')
    
    def is_user_conscious(self, user_id):
        """Check if user is conscious (health > 0)"""
        stats_core = self.get_stats_core()
        if not stats_core:
            return True  # Assume conscious if stats unavailable
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return True  # Assume conscious if no stats
        
        return stats['health'] > 0
    
    async def check_consciousness(self, interaction):
        """Check if user is conscious, send error if not"""
        if not self.is_user_conscious(interaction.user.id):
            await interaction.response.send_message(
                "❌ You are unconscious and cannot perform this action! "
                "Focus on survival - seek medical attention or wait for stabilization.",
                ephemeral=True
            )
            return False
        return True

    @app_commands.command(name="balance", description="Check your or another user's balance")
    @app_commands.describe(user="User to check balance for (leave empty for yourself)")
    @app_commands.guilds(GUILD)
    async def balance(self, interaction: discord.Interaction, user: discord.Member = None):
        # Allow checking others' balances even while unconscious, but not your own
        if not user and not await self.check_consciousness(interaction):
            return
        
        logging.info(f'Balance activated by {interaction.user} in #{interaction.channel}.')
        
        if not user:
            user = interaction.user
        
        _BALANCE = BALANCE(user)
        EMBED = discord.Embed(
            colour=discord.Colour.green(),
            title=str(user),
            timestamp=interaction.created_at
        )
        EMBED.set_author(
            name=f'{interaction.user} used /balance.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_thumbnail(url=user.avatar.url if user.avatar else None)
        EMBED.add_field(name="Cash:", value=f"₪{_BALANCE[0]}")
        EMBED.add_field(name="Bank:", value=f"₪{_BALANCE[1]}")
        EMBED.add_field(name="Balance:", value=f"₪{_BALANCE[2]}")
        EMBED.add_field(name="Credit:", value=f"{_BALANCE[3]*100}%")
        EMBED.add_field(name="Tax Credits:", value=f"₪{_BALANCE[5]}")  # Display tax credits
        EMBED.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=EMBED)
        logging.info(f'Balance complete: {user}')

    @app_commands.command(name="deposit", description="Deposit money into the bank")
    @app_commands.describe(amount="Amount to deposit")
    @app_commands.guilds(GUILD)
    async def deposit(self, interaction: discord.Interaction, amount: int):
        if not await self.check_consciousness(interaction):
            return
        
        logging.info(f'Deposit activated by {interaction.user} in #{interaction.channel}.')
        
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
            
        try:
            _TIME = interaction.created_at
            DEPOSIT(interaction.user, amount, _TIME)
            await interaction.response.send_message(f"Deposited ₪{amount} in the Bank.")
            
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME=_TIME,
                    USER=interaction.user,
                    REASON="DEPOSIT",
                    CASH=-amount,
                    BANK=amount,
                    MESSAGE=None  # No message object for slash commands
                )
                await MONEY_LOG.send(embed=EMBED)
        except ValueError as e:
            logging.error(f"ValueError: {e}")
            await interaction.response.send_message("Invalid amount.", ephemeral=True)
        
        logging.info(f'Deposit complete.')

    @app_commands.command(name="withdraw", description="Withdraw money from the bank")
    @app_commands.describe(amount="Amount to withdraw")
    @app_commands.guilds(GUILD)
    async def withdraw(self, interaction: discord.Interaction, amount: int):
        if not await self.check_consciousness(interaction):
            return
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
            
        try:
            withdrawal_time = interaction.created_at
            WITHDRAW(interaction.user, amount, withdrawal_time)
            await interaction.response.send_message(f"Withdrew ₪{amount} from the Bank.")
            
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=interaction.user,
                    REASON="WITHDRAW",
                    CASH=amount,
                    BANK=-amount,
                    MESSAGE=None
                )
                await MONEY_LOG.send(embed=EMBED)
        except ValueError:
            await interaction.response.send_message("Invalid amount.", ephemeral=True)
            logging.exception("Invalid amount.")
        except Exception as e:
            await interaction.response.send_message("An error occurred while processing your withdrawal.", ephemeral=True)
            logging.exception("Error occurred during withdrawal processing.")
        
        logging.info(f'Withdrawal complete.')

    @app_commands.command(name="pay", description="Pay money to another user")
    @app_commands.describe(user="User to pay", amount="Amount to pay")
    @app_commands.guilds(GUILD)
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if not await self.check_consciousness(interaction):
            return
        
        logging.info(f'Payment initiated by {interaction.user} in #{interaction.channel}.')
        
        if user == interaction.user:
            await interaction.response.send_message("You cannot pay money to yourself!", ephemeral=True)
            return
            
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
            
        try:
            RESULT = PAY(interaction.user, user, amount)
            STRING = RESULT[0]
            actual_tax = RESULT[1]
            credits_used = RESULT[4] if len(RESULT) > 4 else 0
            
            await interaction.response.send_message(STRING)
            logging.info(f'Payment complete.')
            
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=interaction.user,
                    REASON="PAY",
                    CASH=-amount,
                    MESSAGE=None
                )
                await MONEY_LOG.send(embed=EMBED)
                
                # Show net amount received (after tax and credits)
                net_received = amount - actual_tax
                EMBED = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=user,
                    REASON="PAY",
                    CASH=net_received,
                    MESSAGE=None
                )
                # Add tax credit usage info to embed if applicable
                if credits_used > 0:
                    EMBED.add_field(
                        name="💳 Tax Credits Used",
                        value=f"₪{credits_used}",
                        inline=True
                    )
                await MONEY_LOG.send(embed=EMBED)
        except ValueError as e:
            logging.error(f"ValueError: {e}")
            await interaction.response.send_message(str(e), ephemeral=True)
            traceback.print_exc()

    @app_commands.command(name="donate", description="Donate money to the Church (earn tax credits)")
    @app_commands.describe(amount="Amount to donate")
    @app_commands.guilds(GUILD)
    async def donate(self, interaction: discord.Interaction, amount: int):
        if not await self.check_consciousness(interaction):
            return
        
        logging.info(f'Donation initiated by {interaction.user} in #{interaction.channel}.')
        
        if amount <= 0:
            await interaction.response.send_message("Amount must be greater than 0.", ephemeral=True)
            return
        
        try:
            # Check if user has enough cash
            user_balance = BALANCE(interaction.user)
            user_cash = user_balance[0]
            
            if user_cash < amount:
                await interaction.response.send_message(f"❌ Insufficient funds! You have ₪{user_cash} but need ₪{amount}.", ephemeral=True)
                return
            
            # Deduct money from user
            UPDATE_BALANCE(interaction.user, -amount, "CASH")
            
            # Add money to Church treasury
            church_balance = update_treasury_balance("CHURCH", amount)
            
            # Calculate and add tax credits (10% of donation)
            tax_credit_amount = int(amount / 10)
            if tax_credit_amount > 0:
                new_credit_total = ADD_TAX_CREDITS(interaction.user, tax_credit_amount)
            else:
                new_credit_total = user_balance[5]  # Current tax credits
            
            # Create response embed
            embed = discord.Embed(
                title="⛪ Donation to the Church",
                description=f"**{interaction.user.display_name}** has made a generous donation!",
                color=0xffd700
            )
            
            embed.add_field(
                name="💰 Donation Amount",
                value=f"₪{amount:,}",
                inline=True
            )
            
            if tax_credit_amount > 0:
                embed.add_field(
                    name="💳 Tax Credits Earned",
                    value=f"₪{tax_credit_amount:,}",
                    inline=True
                )
                
                embed.add_field(
                    name="📊 Total Tax Credits",
                    value=f"₪{new_credit_total:,}",
                    inline=True
                )
            
            embed.add_field(
                name="⛪ Church Treasury",
                value=f"₪{church_balance:,}",
                inline=False
            )
            
            embed.set_footer(text="Thank you for your generous contribution! • Tax credits = 10% of donation")
            
            await interaction.response.send_message(embed=embed)
            
            # Log the transaction
            MONEY_LOG = self.bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                log_embed = BALANCE_UPDATED(
                    TIME=interaction.created_at,
                    USER=interaction.user,
                    REASON="CHURCH DONATION",
                    CASH=-amount,
                    MESSAGE=None
                )
                if tax_credit_amount > 0:
                    log_embed.add_field(
                        name="💳 Tax Credits Earned",
                        value=f"₪{tax_credit_amount}",
                        inline=True
                    )
                await MONEY_LOG.send(embed=log_embed)
            
            logging.info(f'{interaction.user} donated ₪{amount} to Church, earned ₪{tax_credit_amount} tax credits')
            
        except Exception as e:
            logging.error(f"❌ Error during donation: {e}")
            await interaction.response.send_message("❌ An error occurred during the donation. Please try again.", ephemeral=True)

    @app_commands.command(name="economy", description="View economy statistics")
    @app_commands.guilds(GUILD)
    async def economy(self, interaction: discord.Interaction):
        # Allow viewing economy stats even while unconscious
        _ECONOMY = ECONOMY()
        EMBED = discord.Embed(
            colour=discord.Colour.green(),
            timestamp=interaction.created_at
        )
        EMBED.set_author(
            name=f'{interaction.user} used /economy.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        EMBED.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # User economy
        EMBED.add_field(name="💰 Total Cash:", value=f"₪{_ECONOMY[0]:,}", inline=True)
        EMBED.add_field(name="🏦 Total Bank:", value=f"₪{_ECONOMY[1]:,}", inline=True)
        EMBED.add_field(name="👥 User Balance:", value=f"₪{_ECONOMY[2]:,}", inline=True)
        
        # Treasury information
        EMBED.add_field(name="🏛️ Treasury:", value=f"₪{_ECONOMY[3]:,}", inline=True)
        EMBED.add_field(name="⛪ Church:", value=f"₪{_ECONOMY[4]:,}", inline=True)
        EMBED.add_field(name="🦘 Kangaroo:", value=f"₪{_ECONOMY[5]:,}", inline=True)
        
        # Total system wealth
        EMBED.add_field(name="🌍 **Total System Wealth:**", value=f"**₪{_ECONOMY[6]:,}**", inline=False)
        
        EMBED.set_footer(
            text="Treasury balances are included in total system wealth calculations",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )
        
        await interaction.response.send_message(embed=EMBED)
        logging.info(f'ECONOMY complete: \nUsers: ₪{_ECONOMY[2]:,}, Treasuries: ₪{_ECONOMY[3] + _ECONOMY[4] + _ECONOMY[5]:,}, Total: ₪{_ECONOMY[6]:,}')

    @app_commands.command(name="leaderboard", description="View the wealth leaderboard")
    @app_commands.guilds(GUILD)
    async def leaderboard(self, interaction: discord.Interaction):
        # Allow viewing leaderboard even while unconscious
        EMBED = LEADERBOARD()
        await interaction.response.send_message(embed=EMBED)

    @app_commands.command(name="portfolio", description="View your or another user's investment portfolio")
    @app_commands.describe(user="User to view portfolio for (leave empty for yourself)")
    @app_commands.guilds(GUILD)
    async def portfolio(self, interaction: discord.Interaction, user: discord.Member = None):
        # Allow checking others' portfolios even while unconscious, but not your own
        if not user and not await self.check_consciousness(interaction):
            return
        
        if not user:
            user = interaction.user
            
        logging.info(f'Portfolio activated by {interaction.user} in #{interaction.channel}.')
        
        PORTFOLIO = VIEW_PORTFIOLIO(user)
        PORTFOLIO.timestamp = interaction.created_at
        PORTFOLIO.set_author(
            name=f'{interaction.user} used /portfolio.',
            icon_url=interaction.user.avatar.url if interaction.user.avatar else None
        )
        PORTFOLIO.set_footer(icon_url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=PORTFOLIO)
        logging.info(f'Portfolio complete.')

async def setup(bot):
    await bot.add_cog(EconomyCommands(bot))