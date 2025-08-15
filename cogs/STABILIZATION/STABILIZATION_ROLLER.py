import random

class StabilizationRoller:
    """Handles stabilization roll mechanics - pure logic, no dependencies"""
    
    def make_stabilization_roll(self, current_health):
        """Make a stabilization roll and return result"""
        roll = random.randint(1, 20)
        success = roll >= 10
        
        # Calculate special effects
        special_effect = None
        health_change = 0
        
        if current_health == 0:
            if roll == 20:
                special_effect = "natural_20_stabilize"
                health_change = 1
            elif roll == 1:
                special_effect = "natural_1_critical"
                health_change = -2
        elif current_health < 0:
            if roll == 20:
                special_effect = "natural_20_restore"
                health_change = 2
            elif roll == 1:
                special_effect = "natural_1_critical"
                health_change = -2
        
        return {
            'roll': roll,
            'success': success,
            'special_effect': special_effect,
            'health_change': health_change
        }