import json
import logging
from decimal import Decimal

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

TREASURY_DATA = 'SHEKELS/TREASURY_DATA.JSON'
USER_DATA = 'SHEKELS/USER_DATA.JSON'

def init_treasury():
    """Initialize treasury data file if it doesn't exist"""
    try:
        with open(TREASURY_DATA, 'r') as file:
            data = json.load(file)
        return data
    except FileNotFoundError:
        # Create default treasury data
        default_data = {
            "TREASURY": "0",
            "CHURCH": "0", 
            "KANGAROO": "0"
        }
        with open(TREASURY_DATA, 'w') as file:
            json.dump(default_data, file, indent=4)
        logging.info("Created new treasury data file")
        return default_data

def get_treasury_balance(treasury_type="TREASURY"):
    """Get balance of specific treasury"""
    data = init_treasury()
    return Decimal(data.get(treasury_type, "0"))

def update_treasury_balance(treasury_type, amount):
    """Update treasury balance by adding amount (can be negative)"""
    data = init_treasury()
    current_balance = Decimal(data.get(treasury_type, "0"))
    new_balance = current_balance + Decimal(amount)
    data[treasury_type] = str(new_balance)
    
    with open(TREASURY_DATA, 'w') as file:
        json.dump(data, file, indent=4)
    
    logging.info(f"Updated {treasury_type}: {current_balance} -> {new_balance}")
    return new_balance

def update_user_cash(user_id, amount):
    """Update a specific user's cash balance"""
    try:
        with open(USER_DATA, 'r') as file:
            data = json.load(file)
        
        user_id_str = str(user_id)
        if user_id_str in data:
            current_cash = Decimal(data[user_id_str]["CASH"])
            new_cash = current_cash + Decimal(amount)
            data[user_id_str]["CASH"] = str(new_cash)
            
            with open(USER_DATA, 'w') as file:
                json.dump(data, file, indent=4)
            
            logging.info(f"Updated user {user_id} cash: {current_cash} -> {new_cash}")
            return new_cash
        else:
            logging.error(f"User {user_id} not found in user data")
            return None
    except Exception as e:
        logging.error(f"Error updating user cash: {e}")
        return None

def get_all_treasury_balances():
    """Get all treasury balances"""
    data = init_treasury()
    return {
        "treasury": Decimal(data["TREASURY"]),
        "church": Decimal(data["CHURCH"]),
        "kangaroo": Decimal(data["KANGAROO"])
    }

def pay_treasury(amount):
    """Distribute payment to treasuries according to the existing formula"""
    if amount <= 0:
        return None
        
    import math
    
    KANGAROO_USER_ID = 290699670211002368
    
    half = int(math.floor(amount/2))
    tithe = int(math.ceil(amount/10))
    remaining = amount - (2*tithe + half)
    
    # Update treasury balances
    treasury_balance = update_treasury_balance("TREASURY", half)
    church_balance = update_treasury_balance("CHURCH", tithe)
    
    # Pay the kangaroo tithe directly to the user's cash balance
    kangaroo_cash_balance = update_user_cash(KANGAROO_USER_ID, tithe)
    
    # The remaining amount goes back to the general treasury
    if remaining > 0:
        treasury_balance = update_treasury_balance("TREASURY", remaining)
    
    if kangaroo_cash_balance is not None:
        result_string = (
            f"Paid ₪{amount} to the Treasury. "
            f"₪{tithe} given to His Hoppiness (User {KANGAROO_USER_ID}) and ₪{tithe} to Waffleminster; "
            f"₪{half + remaining} went to the Treasury.\n\n"
            f"The Treasury now holds ₪{treasury_balance}."
        )
    else:
        # Fallback to old method if user update fails
        logging.warning(f"Failed to update user {KANGAROO_USER_ID} cash, using kangaroo treasury instead")
        kangaroo_balance = update_treasury_balance("KANGAROO", tithe)
        result_string = (
            f"Paid ₪{amount} to the Treasury. "
            f"₪{tithe} given to His Hoppiness (treasury) and ₪{tithe} to Waffleminster; "
            f"₪{half + remaining} went to the Treasury.\n\n"
            f"The Treasury now holds ₪{treasury_balance}."
        )
    
    logging.info(result_string)
    return result_string, half + remaining, tithe, tithe