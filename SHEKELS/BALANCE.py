import json
import logging
import discord

from decimal import Decimal

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

USER_DATA = 'SHEKELS/USER_DATA.JSON'


def BALANCE(USER):
    logging.debug("BALANCE Activating.")
    USER_ID = str(USER.id)
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)

    if (USER_ID) in DATA:
        logging.debug("ID found.")
        CASH = Decimal(DATA[USER_ID]["CASH"])
        BANK = Decimal(DATA[USER_ID]["BANK"])
        CREDIT = Decimal(DATA[USER_ID]["CREDIT"])
        _BALANCE = CASH + BANK
        PORTFOLIO = DATA[USER_ID]["PORTFOLIO"]
        logging.debug(f"BALANCE: {_BALANCE}")
        RETURN = CASH, BANK, _BALANCE, CREDIT, PORTFOLIO
    else:
        logging.debug("ID not found.")
        DATA[USER_ID] = {
            "CASH": "0",
            "BANK": "0",
            "CREDIT": "1",
            "TAX": True,
            "NAME": str(USER),
            "LOANS": [],
            "PORTFOLIO": {}
        }
        if DATA is not None:
            with open(USER_DATA, 'w') as file:
                json.dump(DATA, file, indent=4)
        else:
            raise Exception("NO DATA TO DUMP")
        RETURN = 0, 0, 0, 1, {}
    logging.debug("BALANCE Complete.")
    return RETURN
    

def ECONOMY():
    logging.debug("ECONOMY() activated.")
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)

    CASH = 0
    BANK = 0

    for USER in DATA:
        CASH += Decimal(DATA[USER]["CASH"])
        BANK += Decimal(DATA[USER]["BANK"])
    
    BALANCE = CASH+BANK
    
    logging.debug("ECONOMY() complete.")
    return CASH, BANK, BALANCE


def LEADERBOARD():
    logging.debug("LEADERBOARD activated.")
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)
    BALANCES = {}
    for USER, data in DATA.items():
        balance = int(data["BANK"]) + int(data["CASH"])
        if balance:
            BALANCES[USER] = balance
    LEADERBOARd = dict(sorted(BALANCES.items(), key=lambda x: x[1], reverse=True))

    EMBED = discord.Embed(
        colour=discord.Colour.blue(),
        description = ""
        )
    i = 0
    for USER, _BALANCE in LEADERBOARd.items():
        i += 1
        EMBED.description = EMBED.description + f"{i}. `{DATA[USER]['NAME']}`, • ₪{_BALANCE}\n"
        if i >= 10:
            break
    return EMBED
    

def VIEW_PORTFIOLIO(USER):
    STOCKS = BALANCE(USER)[4]
    RETURN = discord.Embed(
        colour=discord.Colour.green(),
        title=USER
    )
    RETURN.set_thumbnail(url=USER.avatar.url)
    try:
        for STOCK, COUNT in STOCKS.items():
            RETURN.add_field(name=STOCK, value=COUNT)

        return RETURN
    except TypeError as e:
        logging.error(f"TypeError: {e}; {STOCKS}")

