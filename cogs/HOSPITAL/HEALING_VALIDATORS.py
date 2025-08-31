# HEALING_VALIDATORS.py
class HealingValidators:
    """Validation logic for healing operations"""
    
    def __init__(self, bot):
        self.bot = bot
    
    '''def is_user_in_combat(self, user_id):
        """Check if user is in combat"""
        # Check if combat reactions system exists
        combat_reactions = self.bot.get_cog('StatsCombatReactions')
        if combat_reactions and hasattr(combat_reactions, 'has_pending_reaction'):
            return combat_reactions.has_pending_reaction(user_id)
        
        # Check if combat manager has cooldowns
        combat_manager = self.bot.get_cog('StatsCombatManager')
        if combat_manager and hasattr(combat_manager, 'is_on_cooldown'):
            return combat_manager.is_on_cooldown(user_id)
        
        # Legacy combat system check
        combat_cog = self.bot.get_cog('StatsCombat')
        if combat_cog and hasattr(combat_cog, 'is_user_in_combat'):
            return combat_cog.is_user_in_combat(user_id)
        
        return False'''
    
    def validate_user_stats(self, user_id):
        """Validate user has stats and get them"""
        stats_core = self.bot.get_cog('StatsCore')
        if not stats_core:
            return None, "Stats system not available"
        
        if not hasattr(stats_core, 'get_user_stats'):
            return None, "Stats system missing required methods"
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return None, "No user stats found. Ask an admin to assign stats!"
        
        return stats, None
    
    def validate_healing_amount(self, amount, current_health, max_health):
        """Validate healing amount is reasonable"""
        
        return True, None