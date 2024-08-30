import json
import math
import logging

from SHEKELS.BALANCE import BALANCE, ECONOMY
from decimal import Decimal

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

USER_DATA = 'SHEKELS/USER_DATA.JSON'


def PAY_TREASURY(AMOUNT, DATA):
    logging.debug("PAY_TREASURY activated.")
    if AMOUNT <= 0:
        return DATA, None
    if not DATA:
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)

    TREASURY = "292226625742045186"
    CHURCH = "802814593930887208"
    KANGAROO = "290699670211002368"

    HALF = int(math.floor(AMOUNT/2))
    TITHE = int(math.ceil(AMOUNT/10))
    BANK = AMOUNT-(2*TITHE+HALF)

    TREASURY_DECIMAL = Decimal(DATA[TREASURY]["BANK"])
    CHURCH_DECIMAL = Decimal(DATA[CHURCH]["BANK"])
    KANGAROO_DECIMAL = Decimal(DATA[KANGAROO]["BANK"])
    
    TREASURY_DECIMAL += HALF
    CHURCH_DECIMAL += TITHE
    KANGAROO_DECIMAL += TITHE

    if DATA is not None:
        DATA[TREASURY]["BANK"] = str(TREASURY_DECIMAL)
        DATA[CHURCH]["BANK"] = str(CHURCH_DECIMAL)
        DATA[KANGAROO]["BANK"] = str(KANGAROO_DECIMAL)
        with open(USER_DATA, 'w') as file:
            json.dump(DATA, file, indent=4)
    else:
        raise Exception("NO DATA TO DUMP")

    TREASURY_CASH = Decimal(DATA[TREASURY]["CASH"])
    TREASURY_BALANCE = TREASURY_CASH + TREASURY_DECIMAL
    STRING = f"Paid ₪{AMOUNT} to the Treasury. ₪{TITHE} given to His Hoppiness and ₪{TITHE} to Waffleminster; ₪{BANK} returned to the Bank.\n\nThe Treasury now holds ₪{TREASURY_BALANCE}."
    logging.info(STRING)
    logging.debug("PAY_TREASURY complete.")
    return DATA, STRING, HALF, TITHE


def WEALTH_TAX(AMOUNT=0.1, MODE=1):
    if AMOUNT <= 0:
        raise ValueError
    
    THRESHOLD = Decimal(ECONOMY()[2]/200)

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
    if TAXES:
        RETURN += PAY_TREASURY(TAXES, DATA)[1]
    return RETURN
