import random
import json
import logging
import math
import datetime
import decimal

from SHEKELS.BALANCE import BALANCE, USE_TAX_CREDITS
from SHEKELS.TREASURY import pay_treasury  # Import new treasury system
from UTILS.FUNCTIONS import CREDIT_SCORE
from decimal import Decimal

USER_DATA = 'UTILS/USER_DATA.JSON'


def ADD_MONEY(USER, AMOUNT, TIME, TYPE="BANK"):
    logging.debug("ADD_MONEY activated.")
    if AMOUNT:
        if TYPE == "CASH":
            UPDATE_BALANCE(USER, AMOUNT, TYPE)
        elif TYPE == "BANK":
            USER_ID = str(USER.id)
            AMOUNT = Decimal(AMOUNT)
            with open(USER_DATA, 'r') as file:
                DATA = json.load(file)
            if AMOUNT > 0:
                D = DEPOSIT(USER, AMOUNT, TIME)
            else:
                D = WITHDRAW(USER, -AMOUNT, TIME)
            DATA[USER_ID]["BANK"] = D[USER_ID]["BANK"]
            if DATA:
                with open(USER_DATA, 'w') as file:
                    json.dump(DATA, file, indent=4)
            else:
                raise Exception("NO DATA TO DUMP")
        else:
            raise TypeError(f"{TYPE} is not a valid Type.")
        
    else:
        raise ValueError("No Amount given.")


def DEPOSIT(USER, AMOUNT, TIME):
    logging.debug("DEPOSIT() activated.")
    AMOUNT = Decimal(AMOUNT)
    USER_ID = str(USER.id)
    _BALANCE = BALANCE(USER)
    if AMOUNT > 0:
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)
        CASH = Decimal(DATA[USER_ID]["CASH"])
        BANK = Decimal(DATA[USER_ID]["BANK"])
        CASH -= AMOUNT
        BANK += AMOUNT
        if _BALANCE[1] < 0:
            _COUNTER = AMOUNT
            for LOAN in DATA[USER_ID]["LOANS"]:
                AMOUNT_DUE = Decimal(LOAN["AMOUNT DUE"])
                if AMOUNT_DUE and _COUNTER:
                    REMAINING = max(0, _COUNTER-AMOUNT_DUE)
                    AMOUNT_DUE = max(0, AMOUNT_DUE-_COUNTER)
                    _COUNTER = REMAINING
                    if not AMOUNT_DUE:
                        LOAN["REPAID"] = str(TIME)
                        try:
                            CREDIT_DECIMAL = Decimal(DATA[USER_ID]["CREDIT"])
                            CREDIT_SCORE_DECIMAL = CREDIT_SCORE(
                                LOAN["DUE"],
                                LOAN["REPAID"],
                                LOAN["PROPORTION"])
                        except decimal.InvalidOperation as e:
                            logging.error("Error converting string to Decimal:", e)
                        
                        CREDIT_DECIMAL = min(1000, (CREDIT_DECIMAL * CREDIT_SCORE_DECIMAL))
                        DATA[USER_ID]["CREDIT"] = str(CREDIT_DECIMAL)
                    LOAN["AMOUNT DUE"] = str(AMOUNT_DUE)
        
        DATA[USER_ID]["CASH"] = str(CASH)
        DATA[USER_ID]["BANK"] = str(BANK)
        if DATA is not None:
            with open(USER_DATA, 'w') as file:
                json.dump(DATA, file, indent=4)
        else:
            raise Exception("NO DATA TO DUMP")
        logging.info(f'{USER} deposited ₪{AMOUNT} in the Bank.')
        return DATA
    else:
        logging.error("Invalid amount.")
        raise ValueError("Invalid amount.")


def PAY(AGENT, PATIENT, AMOUNT):
    if AGENT == PATIENT:
        raise ValueError(f"You cannot pay money to yourself!")
    AGENT_ID = str(AGENT.id)
    PATIENT_ID = str(PATIENT.id)
    AGENT_BALENCE = BALANCE(AGENT)[0]
    PATIENT_BALENCE = BALANCE(PATIENT)

    if AGENT_BALENCE < AMOUNT:
        raise ValueError(f"Insufficient funds.")
    if AMOUNT <= 0:
        raise ValueError("Invalid amount.")
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)
    
    # Calculate initial tax amount
    initial_tax = 0
    if DATA is not None and DATA[PATIENT_ID]["TAX"] and AMOUNT >= 100:
        initial_tax = int(math.floor(AMOUNT/100)*10)
    
    # Use tax credits to reduce the tax
    credits_used = 0
    actual_tax = initial_tax
    if initial_tax > 0:
        credits_used, actual_tax = USE_TAX_CREDITS(PATIENT, initial_tax)

    AGENT_CASH = Decimal(DATA[AGENT_ID]["CASH"])
    PATIENT_CASH = Decimal(DATA[PATIENT_ID]["CASH"])
    AGENT_CASH -= AMOUNT
    PATIENT_CASH += AMOUNT - actual_tax  # Only deduct the actual tax after credits
    DATA[AGENT_ID]["CASH"] = str(AGENT_CASH)
    DATA[PATIENT_ID]["CASH"] = str(PATIENT_CASH)
    
    # Save user data first
    if DATA is not None:
        with open(USER_DATA, 'w') as file:
            json.dump(DATA, file, indent=4)
    else:
        raise Exception("NO DATA TO DUMP")
    
    HALF = 0
    TITHE = 0
    if actual_tax > 0:
        # Use new treasury system
        treasury_result = pay_treasury(actual_tax)
        if treasury_result:
            HALF = treasury_result[1]  # Amount to treasury
            TITHE = treasury_result[2]  # Amount to church/kangaroo

    # Create message showing tax credit usage
    if credits_used > 0:
        if actual_tax > 0:
            STRING = f"{AGENT} paid ₪{AMOUNT} to {PATIENT}. Tax: ₪{initial_tax} (₪{credits_used} covered by credits, ₪{actual_tax} paid)."
        else:
            STRING = f"{AGENT} paid ₪{AMOUNT} to {PATIENT}. Tax: ₪{initial_tax} (fully covered by credits)."
    else:
        STRING = f"{AGENT} paid ₪{AMOUNT} to {PATIENT}, who paid ₪{actual_tax} in taxes."
    
    logging.info(STRING)
    return STRING, actual_tax, HALF, TITHE, credits_used


def UPDATE_BALANCE(USER, AMOUNT, TYPE):
    logging.debug(f"UPDATE_BALANCE activated.")
    AMOUNT = Decimal(AMOUNT)
    USER_ID = str(USER.id)
    BALANCE(USER)
    if AMOUNT:
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)
        _BALANCE = Decimal(DATA[USER_ID][TYPE])
        _BALANCE += AMOUNT
        DATA[USER_ID][TYPE] = str(_BALANCE)
        DATA[USER_ID]["NAME"] = str(USER)
        if DATA is not None:
            with open(USER_DATA, 'w') as file:
                json.dump(DATA, file, indent=4)
        else:
            raise Exception("NO DATA TO DUMP")
    logging.debug("UPDATE_BALANCE completed.")
    return _BALANCE


def WITHDRAW(USER, AMOUNT, TIME):
    logging.debug(f"WITHDRAW() activated. {TIME}")
    AMOUNT = Decimal(AMOUNT)
    USER_ID = str(USER.id)
    _BALANCE = BALANCE(USER)
    if AMOUNT > 0:
        with open(USER_DATA, 'r') as file:
            DATA = json.load(file)
        CREDIT = Decimal(DATA[USER_ID]["CREDIT"])
        if _BALANCE[2] * CREDIT >= AMOUNT-_BALANCE[1]:
            CASH = Decimal(DATA[USER_ID]["CASH"])
            BANK = Decimal(DATA[USER_ID]["BANK"])
            CASH += AMOUNT
            BANK -= AMOUNT
            if BANK < 0:
                _AMOUNT = min(abs(BANK), AMOUNT)
                DATA[USER_ID]["LOANS"].append({
                    "BORROWED": str(TIME),
                    "AMOUNT": str(_AMOUNT),
                    "AMOUNT DUE": str(_AMOUNT),
                    "PROPORTION": str(_AMOUNT/_BALANCE[2]),
                    "DUE": str(TIME + datetime.timedelta(weeks=1)),
                    "REPAID": None
                    })
            DATA[USER_ID]["CASH"] = str(CASH)
            DATA[USER_ID]["BANK"] = str(BANK)
            if DATA is not None:
                with open(USER_DATA, 'w') as file:
                    json.dump(DATA, file, indent=4)
            else:
                raise Exception("NO DATA TO DUMP")
            logging.info(f'{USER} withdrew ₪{AMOUNT} from the Bank.')
            return DATA
        else:
            logging.error("Insufficient funds.")
            raise ValueError("Insufficient funds.")
    else:
        logging.error("Invalid amount.")
        raise ValueError("Invalid amount.")