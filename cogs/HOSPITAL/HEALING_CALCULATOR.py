class HealingCalculator:
    """Handles all healing cost calculations"""
    
    HEALING_COST_PER_HP = 1000
    
    def calculate_healing_cost(self, current_health, max_health, amount=None):
        """Calculate cost for healing"""
        if amount is None:
            health_needed = max_health - current_health
        else:
            max_possible = max_health - current_health
            health_needed = min(amount, max_possible)
        
        total_cost = health_needed * self.HEALING_COST_PER_HP
        return health_needed, total_cost
    
    def can_afford_healing(self, user_cash, healing_cost):
        """Check if user can afford healing"""
        return user_cash >= healing_cost
    
    async def show_healing_cost(self, interaction, amount=None):
        """Display healing cost information"""
        # Create cost embed and show to user
        pass