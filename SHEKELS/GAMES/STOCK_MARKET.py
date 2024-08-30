import random
import math
import ephem
import json
import discord

from datetime import datetime
from SHEKELS.BALANCE import BALANCE
from SHEKELS.TAX import PAY_TREASURY

USER_DATA = "SHEKELS/USER_DATA.JSON"
STOCK_FILE = "SHEKELS/GAMES/STOCKS.JSON"



def GENERATE_STOCKS(LENGTH):
    LETTERS = ( "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M",
               "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z" )
    
    STOCKS = {}
    
    for i in range(LENGTH):
        NAME_LENGTH = random.randint(3,5)
        NAME = ""
        for j in range (NAME_LENGTH):
            NAME += random.choice(LETTERS)
        
        STOCKS[NAME] = random.randint(1, 200)
    
    STOCKS = dict(sorted(STOCKS.items(), key=lambda item: item[1], reverse=True))
    
    return STOCKS


def SELL_STOCK(BUYER, STOCK):
    global USER_DATA
    global STOCK_FILE

    _BALANCE = BALANCE(BUYER)
    PORTFOLIO = _BALANCE[4]

    if STOCK not in PORTFOLIO.keys() or not PORTFOLIO[STOCK]:
        raise KeyError(f"0 {STOCK} in Portfolio.")

    with open(STOCK_FILE, "r") as file:
        STOCKS = json.load(file)
    
    CASH = _BALANCE[0]
    PRICE = STOCKS[STOCK]
    if PRICE >= 100:
        TAX = int(math.floor(PRICE/100)*10)
    else:
        TAX = 0
    
    CASH += PRICE-TAX
    PORTFOLIO[STOCK] -= 1
    
    BUYER_ID = str(BUYER.id)
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)
    DATA[BUYER_ID]["CASH"] = str(CASH)
    DATA[BUYER_ID]["PORTFOLIO"] = PORTFOLIO
    DATA = PAY_TREASURY(TAX, DATA)[0]
    with open(USER_DATA, 'w') as file:
        json.dump(DATA, file, indent = 4)

    return f"{BUYER} sold 1 {STOCK} for ₪{PRICE} and paid ₪{TAX} in taxes.", PRICE, TAX


def BUY_STOCK(BUYER, STOCK):
    global USER_DATA
    global STOCK_FILE

    with open(STOCK_FILE, "r") as file:
        STOCKS = json.load(file)
    
    _BALANCE = BALANCE(BUYER)
    if STOCK not in STOCKS.keys():
        raise KeyError(f"{STOCK} is not a valid Stock.")
    _BALANCE = BALANCE(BUYER)
    CASH = _BALANCE[0]
    PORTFOLIO = _BALANCE[4]
    PRICE = STOCKS[STOCK]
    if CASH >= PRICE:
        CASH -= PRICE
        if STOCK in PORTFOLIO.keys():
            PORTFOLIO[STOCK] += 1
        else:
            PORTFOLIO[STOCK] = 1
        
        BUYER_ID = str(BUYER.id)
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)
        DATA[BUYER_ID]["CASH"] = str(CASH)
        DATA[BUYER_ID]["PORTFOLIO"] = PORTFOLIO
        with open(USER_DATA, 'w') as file:
            json.dump(DATA, file, indent = 4)

        return PRICE
    else:
        raise ValueError(f"Insufficient funds: ₪{CASH}.")


def STOCK_CHANGE():
    global STOCK_FILE

    with open(STOCK_FILE, 'r') as file:
        STOCKS = json.load(file)

    JULIAN_TIME = ephem.julian_date(datetime.now())
    FLUX = math.sin(JULIAN_TIME)/4
    for STOCK, PRICE in STOCKS.items():
        CHANGE = (random.random()-0.5)/2+FLUX
        CHANGE *= 2*PRICE
        STOCKS[STOCK] = max(int(PRICE+CHANGE), 10)
    STOCKS = dict(sorted(STOCKS.items(), key=lambda item: item[1], reverse=True))
    
    with open(STOCK_FILE, 'w') as file:
        json.dump(STOCKS, file, indent=4)


def VIEW_STOCKS():
    global STOCK_FILE
    with open(STOCK_FILE, 'r') as file:
        STOCKS = json.load(file)

    if not len(STOCKS):
        STOCKS = GENERATE_STOCKS(10)
        
    STOCKS = dict(sorted(STOCKS.items(), key=lambda item: item[1], reverse=True))
    with open(STOCK_FILE, 'w') as file:
        json.dump(STOCKS, file, indent=4)
    
    RETURN = discord.Embed(
        colour= discord.Colour.green()
    )

    for STOCK, PRICE in STOCKS.items():
        RETURN.add_field(name=STOCK, value=f"₪{PRICE}")

    return RETURN


