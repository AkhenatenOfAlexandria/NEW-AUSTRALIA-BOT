import random
import json
import logging
import math
import datetime
import decimal

from SHEKELS.BALANCE import BALANCE
from SHEKELS.TAX import PAY_TREASURY
from FUNCTIONS import CREDIT_SCORE
from decimal import Decimal

USER_DATA = 'SHEKELS/USER_DATA.JSON'


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
    
    if DATA is not None and DATA[PATIENT_ID]["TAX"] and AMOUNT >= 100:
        TAX = int(math.floor(AMOUNT/100)*10)
    else:
        TAX = 0

    AGENT_CASH = Decimal(DATA[AGENT_ID]["CASH"])
    PATIENT_CASH = Decimal(DATA[PATIENT_ID]["CASH"])
    AGENT_CASH -= AMOUNT
    PATIENT_CASH += AMOUNT-TAX
    DATA[AGENT_ID]["CASH"] = str(AGENT_CASH)
    DATA[PATIENT_ID]["CASH"] = str(PATIENT_CASH)
    HALF = 0
    TITHE = 0
    if TAX:
        DATA, _STRING, HALF, TITHE = PAY_TREASURY(TAX, DATA)[0:4]
    
    if DATA is not None:
        with open(USER_DATA, 'w') as file:
            json.dump(DATA, file, indent=4)
    else:
        raise Exception("NO DATA TO DUMP")

    STRING = f"{AGENT} paid ₪{AMOUNT} to {PATIENT}, who paid ₪{TAX} in taxes."
    logging.info(STRING)
    return STRING, TAX, HALF, TITHE


def ROB(ROBBER, VICTIM, AMOUNT):
    ROBBER_ID = str(ROBBER.id)
    VICTIM_ID = str(VICTIM.id)
    ROBBER_BALANCE = BALANCE(ROBBER)
    VICTIM_BALANCE = BALANCE(VICTIM)
    if VICTIM_BALANCE[0] <= 0:
        logging.error(f"{ROBBER} attempted to rob {VICTIM} of ₪{AMOUNT}, but he only has ₪{VICTIM_BALANCE[0]}.")
        raise ValueError("Victim has no Cash to rob.")
    if AMOUNT <= 0 or AMOUNT > VICTIM_BALANCE[0]:
        logging.error(f"{ROBBER} attempted to rob {VICTIM} of ₪{AMOUNT}. He has ₪{VICTIM_BALANCE[0]}.")
        raise ValueError(f"Victim's balance of ₪{VICTIM_BALANCE[0]} is less than ₪{AMOUNT}.")
    if not VICTIM_BALANCE[2]:
        VICTIM_BALANCE[2] = 1
    if not ROBBER_BALANCE[2]:
        ROBBER_BALANCE[2] = 1
    CHANCE = 1-(AMOUNT/VICTIM_BALANCE[0])
    if ROBBER_BALANCE[2] < VICTIM_BALANCE[2]:
        RATIO = (2-(ROBBER_BALANCE[2]/VICTIM_BALANCE[2]))/2
    else:
        RATIO = (VICTIM_BALANCE[2]/ROBBER_BALANCE[2])/2
    
    CHANCE = CHANCE*RATIO
    
    with open(USER_DATA, 'r') as file:
        DATA = json.load(file)

    VICTIM_CASH = Decimal(DATA[VICTIM_ID]["CASH"])
    ROBBER_CASH = Decimal(DATA[ROBBER_ID]["CASH"])
    if CHANCE > random.random():
        if AMOUNT >= 100:
            TAX = int(math.floor(AMOUNT/100)*10)
        else:
            TAX = 0

        VICTIM_CASH -= AMOUNT
        ROBBER_CASH += AMOUNT-TAX
        DATA[VICTIM_ID]["CASH"] = str(VICTIM_CASH)
        DATA[ROBBER_ID]["CASH"] = str(ROBBER_CASH)
        DATA = PAY_TREASURY(TAX, DATA)[0]
        RETURN = f"{ROBBER} robbed {VICTIM} of ₪{AMOUNT} and paid ₪{TAX} in taxes.", True, AMOUNT, TAX
    else:
        FINE = int((1-CHANCE)*AMOUNT*2)
        ROBBER_CASH -= FINE
        RESTITUTION = int(math.floor(FINE/2))
        VICTIM_CASH += RESTITUTION
        DATA[VICTIM_ID]["CASH"] = str(VICTIM_CASH)
        DATA[ROBBER_ID]["CASH"] = str(ROBBER_CASH)
        DATA = PAY_TREASURY(int(math.ceil(FINE/2)), DATA)[0]
        RETURN = f"{ROBBER} tried to rob {VICTIM} and was fined ₪{FINE}.", False, FINE, RESTITUTION
    
    if DATA is not None:
        with open(USER_DATA, 'w') as file:
            json.dump(DATA, file, indent=4)
    else:
        raise Exception("NO DATA TO DUMP")
    
    logging.debug("ROB() complete.")
    return RETURN


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
    
