import discord
import logging
import traceback
import asyncio

from discord.ext import commands, tasks
from ASK import REPLY
from SHEKELS.BALANCE import BALANCE, ECONOMY, VIEW_PORTFIOLIO, LEADERBOARD
from SHEKELS.INCOME import INCOME
from SHEKELS.TRANSFERS import WITHDRAW, DEPOSIT, ROB, PAY, ADD_MONEY
from FUNCTIONS import is_role, CALCULATE_DELAY, BALANCE_UPDATED, USER_FINDER
from SHEKELS.TAX import WEALTH_TAX
from SHEKELS.GAMES.STOCK_MARKET import VIEW_STOCKS, BUY_STOCK, SELL_STOCK, STOCK_CHANGE
from BIBLE.BIBLE import BIBLE
from TOKEN import TOKEN

VERSION = "v. Alpha 1.0.0"

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

ANNOUNCEMENTS_ID = 1110265000876052490
GAMES_ID = 824436480180092969
GENERAL_ID = 574731470900559874
MONEY_LOG_ID = 636723720387428392

# Define intents
intents = discord.Intents.all()
intents.messages = True  # This enables the 'messages' intent, required for most commands
intents.message_content = True
intents.members = True
intents.typing = True
intents.presences = True


# Initialize bot with command prefix and intents
bot = commands.Bot(command_prefix='$', intents=intents)
# Event: Bot is ready
@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}.')
    activity = discord.Game(name=VERSION)
    await bot.change_presence(status=discord.Status.online, activity=activity)
    GENERAL = bot.get_channel(GENERAL_ID)
    if False:
        await GENERAL.send("Hail, Glorious Leader Al-b-st (and also that God guy)!")
    STOCK_DELAY = CALCULATE_DELAY("HOURLY")
    await asyncio.sleep(STOCK_DELAY)
    STOCK_UPDATE.start()
    TAX_DELAY = CALCULATE_DELAY("WEEKLY")
    await asyncio.sleep(TAX_DELAY)
    TREASURY_UPDATE.start()


@bot.event
async def on_message(message):
    # Check if the message sender is not a bot to avoid infinite loops
    
    print(f'{message.created_at}: {message.author} sent message in #{message.channel}: "{message.content}"')
    
    if not message.author.bot:
        X = INCOME(message.author, message.channel)
        MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
        if X and MONEY_LOG:
            _MESSAGE = BALANCE_UPDATED(
                TIME = message.created_at,
                USER = message.author,
                REASON = "CHAT",
                CASH = X,
                MESSAGE = message
            )
            await MONEY_LOG.send(embed=_MESSAGE)
        try:
            await bot.process_commands(message)
        except Exception as e:
            await message.send(e)


# Command: Ask
@bot.command()
async def ask(ctx, *, message=None):
    if message:
        logging.info(f'Ask activated by {ctx.author} in #{ctx.channel}.')
        RESPONSE, ANSWER = REPLY()
        if ANSWER == "Y":
            COLOUR = discord.Colour.green()
        elif ANSWER == "N":
            COLOUR = discord.Colour.red()
        else:
            COLOUR = discord.Colour.blue()
        EMBED = discord.Embed(
            colour = COLOUR,
            title="Thus saith the Glorious Leader:",
            description=RESPONSE,
            timestamp= ctx.message.created_at
        )
        EMBED.set_author(
            name=f'{ctx.author} asked: "{message}"',
            url=ctx.message.jump_url,
            icon_url=ctx.author.avatar.url
            )
        EMBED.set_thumbnail(url="https://i.kym-cdn.com/entries/icons/original/000/011/464/tumblr_m2shy4dIV61ru44ono1_500.jpg")
        EMBED.set_footer(icon_url=ctx.guild.icon.url)
        await ctx.send(embed = EMBED)
        logging.info(f'Ask complete: "{RESPONSE}"')
    else:
        await ctx.send("You did not ask a Question.")


# Command: Balance
@bot.command()
async def balance(ctx, USERNAME: str=None):
    logging.info(f'Balance activated by {ctx.author} in #{ctx.channel}.')
    if not USERNAME:
        # If no User-name is specified, the User is checking his own balance.
        USER = ctx.author
    else:
        USER = USER_FINDER(ctx, USERNAME)

        if not USER:
            await ctx.send(f"User `{USERNAME}` not found.")
            return

    _BALANCE = BALANCE(USER)
    EMBED = discord.Embed(
        colour=discord.Colour.green(),
        title=USER,
        timestamp=ctx.message.created_at
    )
    EMBED.set_author(
            name=f'{ctx.author} used $balance.',
            url=ctx.message.jump_url,
            icon_url=ctx.author.avatar.url
            )
    EMBED.set_thumbnail(url=USER.avatar.url)
    EMBED.add_field(name="Cash:", value=f"₪{_BALANCE[0]}")
    EMBED.add_field(name="Bank:", value=f"₪{_BALANCE[1]}")
    EMBED.add_field(name="Balance:", value=f"₪{_BALANCE[2]}")
    EMBED.add_field(name="Credit:", value=f"{_BALANCE[3]*100}%")
    EMBED.set_footer(icon_url=ctx.guild.icon.url)
    await ctx.send(embed=EMBED)
    logging.info(f'Balance complete: {USER}')


# Command: Bible
@bot.command()
async def bible(ctx, *, message):
    try:
        if message:
            EMBED = BIBLE(message)
            await ctx.send(embed = EMBED)
    except Exception as e:
        await ctx.send(e)

# Command: Buy Stock
@bot.command()
async def buy_stock(ctx, message=None, amount: int=1):
    if message:
        try:
            PRICE = BUY_STOCK(ctx.author, message)
            await ctx.send(f"Bought {amount} {message} for ₪{PRICE}.")
            MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME = ctx.message.created_at,
                    USER = ctx.author,
                    REASON = "STOCK BUY",
                    CASH = -PRICE,
                    MESSAGE = ctx.message
                )
                await MONEY_LOG.send(embed = EMBED)
        except KeyError as e:
            await ctx.send(e)
            logging.error(f"KeyError: {e}")
        except ValueError as e:
            await ctx.send(e)
            logging.error(f"ValueError: {e}")
    else:
        await ctx.send("Specify a Stock to buy.")


# Command: Deposit
@bot.command()
async def deposit(ctx, amount: int=0):
    logging.info(f'Deposit activated by {ctx.author} in #{ctx.channel}.')
    if amount <= 0:
        await ctx.send("Amount must be greater than 0.")
        return
    try:
        _TIME = ctx.message.created_at
        DEPOSIT(ctx.author, amount, _TIME)
        await ctx.send(f"Deposited ₪{amount} in the Bank.")
        MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
        if MONEY_LOG:
            EMBED = BALANCE_UPDATED (
                TIME = _TIME,
                USER = ctx.author,
                REASON = "DEPOSIT",
                CASH = -amount,
                BANK = amount,
                MESSAGE= ctx.message
            )
            await MONEY_LOG.send(embed = EMBED)
    except ValueError as e:
        logging.error(f"ValueError: {e}")
        await ctx.send("Invalid amount.")
    '''except Exception as e:
        logging.error(f"Error: {e}")
        await ctx.send("There was an error processing your Deposit.")'''
    logging.info(f'Deposit complete.')


# Command: Echo
@bot.command()
async def echo(ctx, *, message=None):
    logging.info(f'Echo activated by {ctx.author} in #{ctx.channel}.')
    if message:
        await ctx.send(message)
    else:
        await ctx.send("You did not send a message!")
    logging.info("Echo complete.")


# Command: Economy
@bot.command()
async def economy(ctx):
    _ECONOMY = ECONOMY()
    EMBED = discord.Embed(
        colour=discord.Colour.green(),
        timestamp=ctx.message.created_at
    )
    EMBED.set_author(
            name=f'{ctx.author} used $economy.',
            url=ctx.message.jump_url,
            icon_url=ctx.author.avatar.url
            )
    EMBED.set_thumbnail(url=ctx.guild.icon.url)
    EMBED.add_field(name="Total Cash:", value=f"₪{_ECONOMY[0]}")
    EMBED.add_field(name="Total Bank:", value=f"₪{_ECONOMY[1]}")
    EMBED.add_field(name="Total Balance:", value=f"₪{_ECONOMY[2]}")
    EMBED.set_footer(icon_url=ctx.guild.icon.url)
    await ctx.send(embed=EMBED)
    
    logging.info(f'ECONOMY complete: \n₪{_ECONOMY}')


# Command: Leaderboard
@bot.command()
async def leaderboard(ctx):
    EMBED = LEADERBOARD()
    await ctx.send(embed=EMBED)


# Command: Pay
@bot.command()
async def pay(ctx, username: str=None, amount: int=None):
    logging.info(f'Payment intiated by {ctx.author} in #{ctx.channel}.')
    if username:
        USERNAME = USER_FINDER(ctx, username)
    else:
        await ctx.send("Specify a User to be paid.")
    if not USERNAME:
        await ctx.send(f"User `{username}` not found.")
    elif USERNAME == ctx.author:
        await ctx.send(f"You cannot pay money to yourself!")
    elif not amount:
        await ctx.send("Specify an amount to be paid.")
    elif USERNAME and amount:
        try:
            STRING = PAY(ctx.author, USERNAME, amount)
            await ctx.send(STRING[0])
            logging.info(f'Payment complete.')
            MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED (
                    TIME = ctx.message.created_at,
                    USER = ctx.author,
                    REASON = "PAY",
                    CASH = -amount,
                    MESSAGE= ctx.message
                )
                await MONEY_LOG.send(embed = EMBED)
                EMBED = BALANCE_UPDATED (
                    TIME = ctx.message.created_at,
                    USER = USERNAME,
                    REASON = "PAY",
                    CASH = amount-STRING[1],
                    MESSAGE= ctx.message
                )
                await MONEY_LOG.send(embed = EMBED)
        except ValueError as e:
            logging.error(f"ValueError: {e}")
            await ctx.send(e)
            traceback.print_exc()
        except discord.ext.commands.errors.MemberNotFound as e:
            logging.error(e)
            await ctx.send(f"Error: {e}")


# Command: Ping
@bot.command()
async def ping(ctx):
    bot_ping = round(bot.latency * 1000)  # Convert latency to milliseconds and round it
    STRING = f'{bot_ping} milliseconds'
    EMBED = discord.Embed(
        colour = discord.Colour.blue(),
        description = STRING,
        title = "Pong!",
        timestamp=ctx.message.created_at
    )
    EMBED.set_author(
            name=f'{ctx.author} used $ping.',
            url=ctx.message.jump_url,
            icon_url=ctx.author.avatar.url
            )
    EMBED.set_footer(icon_url=ctx.guild.icon.url)
    await ctx.send(embed=EMBED)


# Command: Portfolio
@bot.command()
async def portfolio(ctx, USERNAME: discord.Member=None):
    if not USERNAME:
        USERNAME = ctx.author
    logging.info(f'Portfolio activated by {ctx.author} in #{ctx.channel}.')
    PORTFOLIO = VIEW_PORTFIOLIO(USERNAME)
    PORTFOLIO.timestamp= ctx.message.created_at
    PORTFOLIO.set_author(
            name=f'{ctx.author} used $portfolio.',
            url=ctx.message.jump_url,
            icon_url=ctx.author.avatar.url
            )
    PORTFOLIO.set_footer(icon_url=ctx.guild.icon.url)
    await ctx.send(embed=PORTFOLIO)
    logging.info(f'Portfolio complete.')


# Command: Rob
@bot.command()
async def rob(ctx, USERNAME: discord.Member=None, amount: int=None):
    if not USERNAME:
        await ctx.send("Specify a User to be robbed.")
    elif not amount:
        await ctx.send("Specify an amount to be robbed.")
    elif USERNAME and amount:
        logging.info(f'Rob attempted by {ctx.author} in #{ctx.channel}.')
        try:
            STRING = ROB(ctx.author, USERNAME, amount)
            await ctx.send(STRING[0])
            MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                if STRING[1]:
                    EMBED = BALANCE_UPDATED (
                        TIME = ctx.message.created_at,
                        USER = ctx.author,
                        REASON = "ROB",
                        CASH = amount-STRING[3],
                        MESSAGE= ctx.message
                    )
                    await MONEY_LOG.send(embed = EMBED)
                    EMBED = BALANCE_UPDATED (
                        TIME = ctx.message.created_at,
                        USER = USERNAME,
                        REASON = "ROB",
                        CASH = -amount,
                        MESSAGE= ctx.message
                    )
                    await MONEY_LOG.send(embed = EMBED)
                else:
                    EMBED = BALANCE_UPDATED (
                        TIME = ctx.message.created_at,
                        USER = ctx.author,
                        REASON = "ROB",
                        CASH = -STRING[2],
                        MESSAGE= ctx.message
                    )
                    await MONEY_LOG.send(embed = EMBED)
                    EMBED = BALANCE_UPDATED (
                        TIME = ctx.message.created_at,
                        USER = USERNAME,
                        REASON = "ROB",
                        CASH = STRING[3],
                        MESSAGE= ctx.message
                    )
                    await MONEY_LOG.send(embed = EMBED)
        
        except TypeError as e:
            logging.error(f"TypeError: {e}")
            traceback.print_exc()
            await ctx.send("Invalid target.")
        except ValueError as e:
            logging.error(f"ValueError: {e}")
            await ctx.send("Invalid amount.")   
        except discord.ext.commands.errors.MemberNotFound as e:
            logging.error(e)
            await ctx.send(f"Error: {e}") 
    

# Command: Sell Stock
@bot.command()
async def sell_stock(ctx, message=None):
    if message:
        try:
            RETURN = SELL_STOCK(ctx.author, message)
            await ctx.send(RETURN[0])
            MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
                EMBED = BALANCE_UPDATED(
                    TIME = ctx.message.created_at,
                    USER = ctx.author,
                    REASON = "STOCK SELL",
                    CASH = RETURN[2]-RETURN[1],
                    MESSAGE = ctx.message
                )
                await MONEY_LOG.send(embed = EMBED)
        except KeyError as e:
            await ctx.send(e)
            logging.error(f"KeyError: {e}")
    else:
        await ctx.send("Specify a Stock to sell.")


# Command: Stockmarket
@bot.command()
async def stockmarket(ctx):
    EMBED = VIEW_STOCKS()
    EMBED.timestamp=ctx.message.created_at
    EMBED.set_thumbnail(url=ctx.guild.icon.url)
    EMBED.set_author(
            name=f'{ctx.author} used $stockmarket.',
            url=ctx.message.jump_url,
            icon_url=ctx.author.avatar.url
            )
    EMBED.set_footer(icon_url=ctx.guild.icon.url)
    await ctx.send(embed=EMBED)
    '''try:
        await ctx.send(VIEW_STOCKS())
    except ValueError as e:
        await ctx.send("There was an error processing your request.")
        logging.error(f"ValueError: {e}")'''


# Command: Withdraw
@bot.command()
async def withdraw(ctx, amount: int=0):
    if amount <= 0:
        await ctx.send("Amount must be greater than 0.")
        return
    try:
        withdrawal_time = ctx.message.created_at
        WITHDRAW(ctx.author, amount, withdrawal_time)
        await ctx.send(f"Withdrew ₪{amount} from the Bank.")
        MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
        if MONEY_LOG:
            EMBED = BALANCE_UPDATED (
                TIME = ctx.message.created_at,
                USER = ctx.author,
                REASON = "WITHDRAW",
                CASH = amount,
                BANK = -amount,
                MESSAGE= ctx.message
            )
            await MONEY_LOG.send(embed = EMBED)
    except ValueError:
        await ctx.send("Invalid amount.")
        logging.exception("Invalid amount.")
    except Exception as e:
        await ctx.send("An error occurred while processing your Withdrawal.")
        logging.exception("Error occurred during withdrawal processing.")
    logging.info(f'Withdrawal complete.')


async def wealthtax_collect(ctx=None):
    ANNOUNCEMENTS = bot.get_channel(ANNOUNCEMENTS_ID)
    if ANNOUNCEMENTS:
        await ANNOUNCEMENTS.send(f"Wealth Tax collected:\n{WEALTH_TAX()}")
    else:
        logging.error("ANNOUNCEMENTS CHANNEL NOT FOUND.")
        

async def stockchange(ctx=None):
    STOCK_CHANGE()
    STRING = "Stock Prices have been updated. Use $stockmarket to view them."
    if ctx:
        await ctx.send(STRING)
    else:
        MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
        if MONEY_LOG:
            await MONEY_LOG.send(STRING)
        else:
            logging.error("MONEY_LOG CHANNEL NOT FOUND.")
        '''except Exception as e:
        await ctx.send("An error occurred.")
        logging.debug(f"Exception: {e}")'''


# Administrator Command: Money
@bot.command()
@is_role("Administrator")
async def money(ctx, username: str = None, amount: int = None, message="BANK"):
    message = message.upper()
    if username:
        USERNAME = USER_FINDER(ctx, username)
    else:
        await ctx.send("Specify a User to be paid.")
    if not USERNAME:
        await ctx.send(f"User `{username}` not found.")
    elif not amount:
        await ctx.send("Specify an Amount.")
    elif message not in {"CASH", "BANK"}:
        await ctx.send(f"Invalid type: {message}")
    else:
        BALANCE(USERNAME)
        ADD_MONEY(USERNAME, amount, ctx.message.created_at, message)
        _BANK = 0
        _CASH = 0
        if message == "BANK":
            _BANK = amount
            STRING = "Bank"
        elif message == "CASH":
            _CASH = amount
            STRING = "Cash"
        if amount > 0:
            ADD = ("Added", "to")
        else:
            ADD = ("Removed", "from")
            amount = -amount
        await ctx.send(f"{ADD[0]} ₪{amount} {ADD[1]} {USERNAME}'s {STRING} balance.")
        MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
        if MONEY_LOG:
           
            EMBED = BALANCE_UPDATED (
                TIME = ctx.message.created_at,
                USER = USERNAME,
                REASON = "MONEY",
                CASH = _CASH,
                BANK = _BANK,
                MESSAGE= ctx.message
            )
            await MONEY_LOG.send(embed = EMBED)


# Administrator Command: Role Money
@bot.command()
@is_role("Administrator")
async def role_money(ctx, role = None, amount: int = None, message = "BANK"):
    ROLE = discord.utils.get(ctx.guild.roles, name=role)
    message = message.upper()

    if not role:
        await ctx.send("Specify a Role.")
        return
    
    if not amount:
        await ctx.send("Specify an Amount.")
        return
    
    if message not in {"CASH", "BANK"}:
        await ctx.send(f"Invalid type: {message}")
        return
    
    if ROLE is None:
        await ctx.send("Role not found.")
        return
    
    ROLE_MEMBERS = ROLE.members

    for MEMBER in ROLE_MEMBERS:
        #try:
            logging.debug(f"Attempting to MONEY {MEMBER}.")
            BALANCE(MEMBER)
            ADD_MONEY(MEMBER, amount, ctx.message.created_at, message)
            _BANK = 0
            _CASH = 0
            if message == "BANK":
                _BANK = amount
            elif message == "CASH":
                _CASH = amount
            MONEY_LOG = bot.get_channel(MONEY_LOG_ID)
            if MONEY_LOG:
            
                EMBED = BALANCE_UPDATED (
                    TIME = ctx.message.created_at,
                    USER = MEMBER,
                    REASON = "MONEY",
                    CASH = _CASH,
                    BANK = _BANK,
                    MESSAGE= ctx.message
                )
                await MONEY_LOG.send(embed = EMBED)
            '''except Exception as e:
            await ctx.send(e)'''
    
    if amount > 0:
        ADD = ("Added", "to")
    else:
        ADD = ("Removed", "from")
        amount = -amount
    NUMBER = len(ROLE_MEMBERS)
    await ctx.send(f"{ADD[0]} ₪{amount} {ADD[1]} {message} balance of {NUMBER} Members.")

# Administrator Command: Stockupdate
@bot.command()
@is_role("Administrator")
async def stockupdate(ctx):
    await stockchange(ctx)
    

# Administrator Command: Wealthtax
@bot.command()
@is_role("Administrator")
async def wealthtax(ctx):
    await wealthtax_collect()
    

# Define a new task that runs periodically every hour
@tasks.loop(hours=168)
async def TREASURY_UPDATE():
    await wealthtax_collect()

@tasks.loop(hours=1)
async def STOCK_UPDATE():
    await stockchange()


# Run bot with token
def BOT():
    logging.info("BOT() activated.")
    bot.run(TOKEN)
    logging.info("BOT() complete.")
