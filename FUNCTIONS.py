import discord
from discord.ext import commands
import datetime
from decimal import Decimal


def USER_FINDER(ctx, USERNAME):
    USER = None
    # Check if the input is a mention
    if USERNAME.startswith('<@') and USERNAME.endswith('>'):
        # Remove the <@ and > characters to extract the ID

        if USERNAME[2] == '!':
            USER_ID = int(USERNAME[3:-1])
        else:
            USER_ID = int(USERNAME[2:-1])

        USER = ctx.guild.get_member(USER_ID)
    else:
        USER = discord.utils.get(ctx.guild.members, name=USERNAME)

        if not USER:
            USER = discord.utils.get(ctx.guild.members, display_name=USERNAME)

        if not USER:
            USER = ctx.guild.get_member(USERNAME)
    return USER


# Define the role check function
def is_role(role_name):
    async def predicate(ctx):
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        if role in ctx.author.roles:
            return True
        else:
            await ctx.send("You do not have the required role to use this command.")
            return False
    return commands.check(predicate)


def CREDIT_SCORE(DUE, PAID, AMOUNT):
    AMOUNT = Decimal(AMOUNT)
    DUE_DATE = datetime.datetime.fromisoformat(DUE)
    PAID_DATE = datetime.datetime.fromisoformat(PAID)
    WEEK = datetime.timedelta(weeks=1)
    HOUR = datetime.timedelta(hours=1)
    EARLY = DUE_DATE - PAID_DATE
    if EARLY < HOUR:
        return 1
    if DUE_DATE > PAID_DATE:
        
        dCREDIT = 1 + AMOUNT*Decimal(EARLY/WEEK)
    if PAID_DATE > DUE_DATE:
        LATE = PAID_DATE - DUE_DATE
        dCREDIT = AMOUNT*Decimal(WEEK/LATE)-1
    return min(dCREDIT, 10)


def CALCULATE_DELAY(INTERVAL):
    CURRENT_TIME = datetime.datetime.now()
    if INTERVAL == "HOURLY":
        DELTA = datetime.timedelta(hours=1)
        DESIRED_TIME = CURRENT_TIME.replace(minute=0, second=0, microsecond=0)
    elif INTERVAL == "WEEKLY":
        SATURDAY = 5
        TODAY = datetime.datetime.today()
        DELTA = datetime.timedelta(weeks=1)
        NEXT = ((SATURDAY - TODAY.weekday()) % 7)
        DESIRED_TIME = (CURRENT_TIME).replace(day=CURRENT_TIME.day+NEXT, hour=0, minute=0, second=0, microsecond=0)
    if CURRENT_TIME > DESIRED_TIME:
        DESIRED_TIME += DELTA
    DELAY = (DESIRED_TIME - CURRENT_TIME).total_seconds()
    return DELAY


def BALANCE_UPDATED(TIME, USER, REASON, CASH=0, BANK=0, MESSAGE=None):
    if CASH + BANK < 0:
        COLOUR = discord.Colour.red()
    elif CASH + BANK:
        COLOUR = discord.Colour.green()
    else:
        COLOUR = discord.Colour.blue()
    EMBED = discord.Embed(
        colour = COLOUR,
        title = "Balance Updated",
        timestamp = TIME
    )
    if REASON == "CHAT":
        EMBED.set_author(
            name=f"{MESSAGE.author} sent message in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    elif REASON == "DEPOSIT":
        EMBED.set_author(
            name=f"{MESSAGE.author} used $deposit in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    elif REASON == "MONEY":
        EMBED.set_author(
            name=f"{MESSAGE.author} used $money in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    elif REASON == "PAY":
        EMBED.set_author(
            name=f"{MESSAGE.author} used $pay in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    elif REASON == "ROB":
        EMBED.set_author(
        name=f"{MESSAGE.author} used $rob in #{MESSAGE.channel}.",
        url=MESSAGE.jump_url,
        icon_url=MESSAGE.author.avatar.url)
    elif REASON == "STOCK BUY":
        EMBED.set_author(
            name=f"{MESSAGE.author} used $buy_stock in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    elif REASON == "STOCK SELL":
        EMBED.set_author(
            name=f"{MESSAGE.author} used $sell_stock in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    elif REASON == "WITHDRAW":
        EMBED.set_author(
            name=f"{MESSAGE.author} used $withdraw in #{MESSAGE.channel}.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    EMBED.add_field(name= "User:", value= USER, inline= False)
    _CASH = CASH
    if CASH > 0:
        _CASH = f"+{CASH}"
    EMBED.add_field(name= "Amount:", value= f"Cash: `{_CASH}` | Bank: `{BANK}`", inline= False)
    return EMBED
