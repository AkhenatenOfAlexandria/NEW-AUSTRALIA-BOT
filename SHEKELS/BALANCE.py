import json
import logging
import discord

from decimal import Decimal

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

USER_DATA = 'SHEKELS/USER_DATA.JSON'
TREASURY_DATA = 'SHEKELS/TREASURY_DATA.JSON'


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
        TAX_CREDITS = Decimal(DATA[USER_ID].get("TAX_CREDITS", "0"))  # Get tax credits, default to 0
        _BALANCE = CASH + BANK
        PORTFOLIO = DATA[USER_ID]["PORTFOLIO"]
        logging.debug(f"BALANCE: {_BALANCE}, TAX_CREDITS: {TAX_CREDITS}")
        RETURN = CASH, BANK, _BALANCE, CREDIT, PORTFOLIO, TAX_CREDITS
    else:
        logging.debug("ID not found.")
        DATA[USER_ID] = {
            "CASH": "0",
            "BANK": "0",
            "CREDIT": "1",
            "TAX_CREDITS": "0",  # Initialize tax credits
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
        RETURN = 0, 0, 0, 1, {}, 0
    logging.debug("BALANCE Complete.")
    return RETURN


def ADD_TAX_CREDITS(USER, AMOUNT):
    """Add tax credits to a user's account"""
    logging.debug(f"ADD_TAX_CREDITS activated for {USER} with amount {AMOUNT}")
    USER_ID = str(USER.id)
    
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)
    
    # Ensure user exists in data
    if USER_ID not in DATA:
        BALANCE(USER)  # This will create the user entry
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)
    
    # Add tax credits
    current_credits = Decimal(DATA[USER_ID].get("TAX_CREDITS", "0"))
    new_credits = current_credits + Decimal(AMOUNT)
    DATA[USER_ID]["TAX_CREDITS"] = str(new_credits)
    
    # Save data
    with open(USER_DATA, 'w') as file:
        json.dump(DATA, file, indent=4)
    
    logging.info(f"Added ₪{AMOUNT} tax credits to {USER}. Total credits: ₪{new_credits}")
    return new_credits


def USE_TAX_CREDITS(USER, TAX_AMOUNT):
    """Use tax credits to reduce tax obligation. Returns (credits_used, remaining_tax)"""
    logging.debug(f"USE_TAX_CREDITS activated for {USER} with tax amount {TAX_AMOUNT}")
    USER_ID = str(USER.id)
    
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)
    
    if USER_ID not in DATA:
        return 0, TAX_AMOUNT  # No credits available
    
    current_credits = Decimal(DATA[USER_ID].get("TAX_CREDITS", "0"))
    tax_amount = Decimal(TAX_AMOUNT)
    
    if current_credits <= 0:
        return 0, tax_amount  # No credits to use
    
    # Calculate how much of the tax can be covered by credits
    credits_used = min(current_credits, tax_amount)
    remaining_tax = tax_amount - credits_used
    remaining_credits = current_credits - credits_used
    
    # Update user's tax credits
    DATA[USER_ID]["TAX_CREDITS"] = str(remaining_credits)
    
    # Save data
    with open(USER_DATA, 'w') as file:
        json.dump(DATA, file, indent=4)
    
    logging.info(f"{USER} used ₪{credits_used} in tax credits. Remaining tax: ₪{remaining_tax}, Remaining credits: ₪{remaining_credits}")
    return credits_used, remaining_tax


def get_treasury_totals():
    """Get total wealth in all treasuries"""
    try:
        with open(TREASURY_DATA, 'r') as file:
            treasury_data = json.load(file)
        
        treasury_total = Decimal(treasury_data.get("TREASURY", "0"))
        church_total = Decimal(treasury_data.get("CHURCH", "0"))
        kangaroo_total = Decimal(treasury_data.get("KANGAROO", "0"))
        
        total_treasury_wealth = treasury_total + church_total + kangaroo_total
        
        logging.debug(f"Treasury totals - Treasury: ₪{treasury_total}, Church: ₪{church_total}, Kangaroo: ₪{kangaroo_total}, Total: ₪{total_treasury_wealth}")
        return treasury_total, church_total, kangaroo_total, total_treasury_wealth
        
    except FileNotFoundError:
        logging.warning("Treasury data file not found, assuming zero treasury wealth")
        return Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")
    except Exception as e:
        logging.error(f"Error reading treasury data: {e}")
        return Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")
    

def ECONOMY():
    logging.debug("ECONOMY() activated.")
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)

    CASH = 0
    BANK = 0

    for USER in DATA:
        CASH += Decimal(DATA[USER]["CASH"])
        BANK += Decimal(DATA[USER]["BANK"])
    
    USER_BALANCE = CASH + BANK
    
    # Get treasury totals
    treasury_total, church_total, kangaroo_total, total_treasury_wealth = get_treasury_totals()
    
    # Calculate total system wealth (users + treasuries)
    TOTAL_SYSTEM_WEALTH = USER_BALANCE + total_treasury_wealth
    
    logging.debug(f"ECONOMY() complete. User wealth: ₪{USER_BALANCE}, Treasury wealth: ₪{total_treasury_wealth}, Total system: ₪{TOTAL_SYSTEM_WEALTH}")
    return CASH, BANK, USER_BALANCE, treasury_total, church_total, kangaroo_total, TOTAL_SYSTEM_WEALTH


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