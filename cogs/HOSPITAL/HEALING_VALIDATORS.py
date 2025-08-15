class HealingValidators:
    """Validation logic for healing operations"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def is_user_in_combat(self, user_id):
        """Check if user is in combat"""
        combat_cog = self.bot.get_cog('StatsCombat')
        if combat_cog and hasattr(combat_cog, 'is_user_in_combat'):
            return combat_cog.is_user_in_combat(user_id)
        return False
    
    def validate_user_stats(self, user_id):
        """Validate user has stats and get them"""
        stats_core = self.bot.get_cog('StatsCore')
        if not stats_core:
            return None, "Stats system not available"
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return None, "No character stats found"
        
        return stats, None
    
    def validate_healing_amount(self, amount, current_health, max_health):
        """Validate healing amount is reasonable"""
        pass