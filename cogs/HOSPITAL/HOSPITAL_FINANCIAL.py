import logging
from datetime import datetime

from SHEKELS.BALANCE import BALANCE
from SHEKELS.TRANSFERS import UPDATE_BALANCE, WITHDRAW

TRANSPORT_COST = 1000  # Cost in shekels for hospital transport
HEALING_COST_PER_HP = 1000   # Cost in shekels per HP healed


class HospitalFinancial:
    """Hospital financial operations - billing, payments, and cost calculations"""
    
    def __init__(self, hospital_core):
        self.core = hospital_core
    
    def calculate_max_affordable_healing(self, user, current_health, max_health):
        """Calculate maximum healing the user can afford"""
        try:
            user_balance = BALANCE(user)
            user_cash = user_balance[0]
            user_bank = user_balance[1]
            user_total = user_balance[2]
            user_credit = user_balance[3]
            
            # Calculate available funds (cash + potential credit)
            available_funds = user_cash
            credit_limit = int(user_total * user_credit)
            if credit_limit > user_cash:
                available_funds = credit_limit
            
            # Calculate how many HP they can afford
            max_affordable_hp = available_funds // HEALING_COST_PER_HP
            
            # Limit to what they actually need (but allow going above 1 HP if they can afford it)
            health_needed = max_health - current_health
            affordable_hp = min(max_affordable_hp, health_needed)
            
            # However, if they're at 0 or negative HP, prioritize getting to at least 1 HP
            if current_health <= 0 and affordable_hp >= 1:
                # They can afford at least stabilization
                return max(1, affordable_hp), affordable_hp * HEALING_COST_PER_HP
            elif current_health <= 0:
                # They can't even afford stabilization
                return 0, 0
            else:
                # They're above 0 HP, heal what they can afford
                return affordable_hp, affordable_hp * HEALING_COST_PER_HP
            
        except Exception as e:
            logging.error(f"❌ Failed to calculate affordable healing: {e}")
            return 0, 0
    
    def charge_for_service(self, user, amount, service_type):
        """
        Charge user for hospital service. Try cash first, then credit if needed.
        Hospital services are not taxed.
        Returns (success, method, actual_cost)
        """
        try:
            user_balance = BALANCE(user)
            user_cash = user_balance[0]
            user_bank = user_balance[1]
            user_total = user_balance[2]
            user_credit = user_balance[3]
            
            # Hospital services are not taxed - use amount directly
            total_cost = amount
            
            # Try to pay with cash first
            if user_cash >= total_cost:
                UPDATE_BALANCE(user, -total_cost, "CASH")
                return True, "cash", total_cost
            
            # Try to use bank funds (which may trigger credit/loan system)
            elif user_total * user_credit >= total_cost:
                try:
                    WITHDRAW(user, total_cost, datetime.now())
                    return True, "credit", total_cost
                except Exception as e:
                    logging.error(f"❌ Credit withdrawal failed: {e}")
                    return False, "insufficient_credit", total_cost
            
            else:
                return False, "insufficient_funds", total_cost
                
        except Exception as e:
            logging.error(f"❌ Failed to charge for service: {e}")
            return False, "error", amount
    
    def get_service_costs(self):
        """Get current service costs"""
        return {
            'transport': TRANSPORT_COST,
            'healing_per_hp': HEALING_COST_PER_HP
        }
    
    def calculate_treatment_cost(self, hp_to_heal):
        """Calculate total cost for healing specified HP"""
        return hp_to_heal * HEALING_COST_PER_HP