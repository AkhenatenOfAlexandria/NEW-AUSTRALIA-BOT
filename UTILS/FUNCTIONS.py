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

def CALCULATE_DELAY(interval: str) -> float:
    now = datetime.datetime.now()

    if interval == "HOURLY":
        delta = datetime.timedelta(hours=1)
        desired = now.replace(minute=0, second=0, microsecond=0)

    elif interval == "MINUTELY":
        delta = datetime.timedelta(minutes=1)
        desired = now.replace(second=0, microsecond=0)

    elif interval == "EVERY_5_MINUTES":
        delta = datetime.timedelta(minutes=5)
        # Align to current 5-min block (00,05,10,...,55)
        base_minute = (now.minute // 5) * 5
        desired = now.replace(minute=base_minute, second=0, microsecond=0)

    elif interval == "WEEKLY":
        # Next Saturday 00:00 local time
        delta = datetime.timedelta(weeks=1)
        days_until_sat = (5 - now.weekday()) % 7  # Monday=0 ... Sunday=6
        desired_date = (now + datetime.timedelta(days=days_until_sat)).date()
        desired = datetime.datetime.combine(desired_date, datetime.time(0, 0))

    else:
        raise ValueError(f"Unknown interval: {interval}")

    if now >= desired:
        desired += delta

    return (desired - now).total_seconds()


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
        # In UTILS/FUNCTIONS.py, line 141:
        EMBED.set_author(
            # In UTILS/FUNCTIONS.py, line 141:
            name=f"{USER} used withdraw command.",
            url=MESSAGE.jump_url,
            icon_url=MESSAGE.author.avatar.url)
    EMBED.add_field(name= "User:", value= USER, inline= False)
    _CASH = CASH
    if CASH > 0:
        _CASH = f"+{CASH}"
    EMBED.add_field(name= "Amount:", value= f"Cash: `{_CASH}` | Bank: `{BANK}`", inline= False)
    return EMBED
