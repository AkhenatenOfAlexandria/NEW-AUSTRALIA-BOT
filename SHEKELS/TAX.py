import json
import math
import logging

from SHEKELS.BALANCE import BALANCE, ECONOMY
from SHEKELS.TREASURY import pay_treasury  # Import new treasury system
from decimal import Decimal

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

USER_DATA = 'SHEKELS/USER_DATA.JSON'


def PAY_TREASURY(AMOUNT, DATA=None):
    """Legacy function - now redirects to new treasury system"""
    logging.debug("PAY_TREASURY activated (legacy redirect).")
    
    if AMOUNT <= 0:
        return DATA, None
        
    # Use new treasury system
    result = pay_treasury(AMOUNT)
    
    if result:
        return DATA, result[0], result[1], result[2]
    else:
        return DATA, None, 0, 0


def WEALTH_TAX(AMOUNT=0.1, MODE=1):
    if AMOUNT <= 0:
        raise ValueError
    
    # Use total system wealth (including treasuries) to calculate wealth tax threshold
    economy_data = ECONOMY()
    total_system_wealth = economy_data[6]  # The 7th element is TOTAL_SYSTEM_WEALTH
    THRESHOLD = Decimal(total_system_wealth/200)
    
    logging.debug(f"Wealth tax threshold calculated: ₪{THRESHOLD} (based on total system wealth: ₪{total_system_wealth})")

    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)
    
    RICH = {}
    for USER in DATA:
        BANK = Decimal(DATA[USER]["BANK"])
        CASH = Decimal(DATA[USER]["CASH"])
        _BALANCE = BANK + CASH
        if _BALANCE > THRESHOLD and DATA[USER]["TAX"]:
            RICH[USER] = int(math.floor(_BALANCE/40)*10)
    
    TAXES = 0
    RETURN = ""
    for USER, TAX in RICH.items():
        BANK = Decimal(DATA[USER]["BANK"])
        BANK -= TAX
        TAXES += TAX
        STRING = f"{DATA[USER]['NAME']} paid ₪{TAX} in taxes."
        RETURN += f"{STRING}\n"
        logging.info(f"{DATA[USER]['NAME']} paid ₪{TAX} in taxes.")
        DATA[USER]["BANK"] = str(BANK)
    
    # Save user data changes
    if DATA is not None:
        with open(USER_DATA, 'w') as file:
            json.dump(DATA, file, indent=4)
    
    if TAXES:
        # Use new treasury system
        treasury_result = pay_treasury(TAXES)
        if treasury_result:
            RETURN += treasury_result[0]
    
    return RETURN