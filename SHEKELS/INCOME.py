import random
import json
import logging
import discord

from decimal import Decimal
from SHEKELS.BALANCE import BALANCE

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

USER_DATA = 'SHEKELS/USER_DATA.JSON'


def INCOME(USER, CHANNEL):
    logging.debug("INCOME() activated.")
    USER_ID = str(USER.id)
    CHANNEL = CHANNEL
    if str(CHANNEL) == "spam":
        return False
    else:
        CASH = BALANCE(USER)[0]
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)
        USER_CASH = Decimal(DATA[USER_ID]["CASH"])
        SHEKELS = random.randint(0, 10)
        USER_CASH = CASH + SHEKELS
        DATA[USER_ID]["CASH"] = str(USER_CASH)
        if DATA is not None:
            with open(USER_DATA, 'w') as file:
                json.dump(DATA, file, indent=4)
        else:
            raise Exception("NO DATA TO DUMP")
        return SHEKELS
    