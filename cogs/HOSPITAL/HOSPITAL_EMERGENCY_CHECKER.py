import logging
from datetime import datetime, timedelta

class HospitalEmergencyChecker:
    """Handles emergency intervention checks"""
    
    def __init__(self, hospital_core, hospital_treatment):
        self.core = hospital_core
        self.treatment = hospital_treatment
    
    async def check_for_emergencies(self):
        """Check for critical cases needing immediate attention"""
        emergency_cases = []
        
        try:
            stats_core = self.core.get_stats_core()
            if not stats_core:
                await self.core.send_error_to_health_log(
                    "Emergency check failed - StatsCore not available",
                    "Cannot assess emergency situations"
                )
                return emergency_cases
            
            all_users = stats_core.get_all_users_with_stats()
            
            for user_id in all_users:
                user_stats = stats_core.get_user_stats(user_id)
                if not user_stats:
                    continue
                
                current_health = user_stats['health']
                
                # Only check unconscious users
                if current_health <= 0:
                    user = self.core.bot.get_user(user_id)
                    if user:
                        emergency_case = await self.categorize_emergency_case(user_id, user, user_stats)
                        if emergency_case:
                            emergency_cases.append(emergency_case)
            
            # Log emergency summary if any cases found
            if emergency_cases:
                critical_count = sum(1 for case in emergency_cases if case['severity'] == 'CRITICAL')
                urgent_count = sum(1 for case in emergency_cases if case['severity'] == 'URGENT')
                blocked_count = sum(1 for case in emergency_cases if case['severity'] == 'BLOCKED')
                
                await self.core.send_warning_to_health_log(
                    f"Emergency assessment complete: {len(emergency_cases)} cases found - "
                    f"{critical_count} critical, {urgent_count} urgent, {blocked_count} blocked by combat",
                    "🚨 Emergency Cases Detected"
                )
            
            return emergency_cases
            
        except Exception as e:
            logging.error(f"❌ Emergency check failed: {e}")
            await self.core.send_error_to_health_log(
                f"Emergency check failed: {str(e)}",
                "Critical error during emergency assessment"
            )
            return emergency_cases
    
    async def categorize_emergency_case(self, user_id, user, stats):
        """Categorize individual emergency case"""
        try:
            current_health = stats['health']
            in_hospital = self.core.is_in_hospital(user_id)
            in_combat = self.core.is_user_in_combat(user_id)
            
            # Calculate max affordable healing to assess if they can be helped
            affordable_hp, cost = self.treatment.financial.calculate_max_affordable_healing(
                user, current_health, stats['constitution'] * 10  # Rough max health calc
            )
            
            emergency_case = {
                'user_id': user_id,
                'username': user.display_name,
                'health': current_health,
                'in_hospital': in_hospital,
                'in_combat': in_combat,
                'affordable_hp': affordable_hp,
                'estimated_cost': cost,
                'timestamp': datetime.now()
            }
            
            # Determine severity and action needed
            if in_combat:
                emergency_case['severity'] = 'BLOCKED'
                emergency_case['action_needed'] = 'WAIT_FOR_COMBAT_END'
                emergency_case['priority'] = 3
                emergency_case['details'] = f"Unconscious in combat ({current_health} HP) - cannot transport"
                
            elif not in_hospital and affordable_hp >= abs(current_health) + 1:
                # Can afford transport + stabilization
                emergency_case['severity'] = 'CRITICAL'
                emergency_case['action_needed'] = 'TRANSPORT_AND_HEAL'
                emergency_case['priority'] = 1
                emergency_case['details'] = f"Unconscious outside hospital ({current_health} HP) - can afford full treatment"
                
            elif not in_hospital and affordable_hp < abs(current_health) + 1:
                # Cannot afford full treatment
                emergency_case['severity'] = 'CRITICAL'
                emergency_case['action_needed'] = 'TRANSPORT_ONLY'
                emergency_case['priority'] = 1
                emergency_case['details'] = f"Unconscious outside hospital ({current_health} HP) - insufficient funds for full healing"
                
            elif in_hospital and affordable_hp >= abs(current_health) + 1:
                # In hospital and can afford healing
                emergency_case['severity'] = 'URGENT'
                emergency_case['action_needed'] = 'HEAL'
                emergency_case['priority'] = 2
                emergency_case['details'] = f"Unconscious in hospital ({current_health} HP) - can afford stabilization"
                
            else:
                # In hospital but cannot afford healing
                emergency_case['severity'] = 'URGENT'
                emergency_case['action_needed'] = 'MONITOR'
                emergency_case['priority'] = 2
                emergency_case['details'] = f"Unconscious in hospital ({current_health} HP) - insufficient funds"
            
            return emergency_case
            
        except Exception as e:
            logging.error(f"❌ Failed to categorize emergency case for {user.display_name}: {e}")
            return None
    
    async def get_emergency_statistics(self):
        """Get statistics about current emergency cases"""
        try:
            emergency_cases = await self.check_for_emergencies()
            
            stats = {
                'total_emergencies': len(emergency_cases),
                'critical_cases': 0,
                'urgent_cases': 0,
                'blocked_cases': 0,
                'treatable_cases': 0,
                'insufficient_funds_cases': 0,
                'timestamp': datetime.now()
            }
            
            for case in emergency_cases:
                if case['severity'] == 'CRITICAL':
                    stats['critical_cases'] += 1
                elif case['severity'] == 'URGENT':
                    stats['urgent_cases'] += 1
                elif case['severity'] == 'BLOCKED':
                    stats['blocked_cases'] += 1
                
                if case['affordable_hp'] > 0:
                    stats['treatable_cases'] += 1
                else:
                    stats['insufficient_funds_cases'] += 1
            
            return stats
            
        except Exception as e:
            logging.error(f"❌ Failed to get emergency statistics: {e}")
            return None
    
    async def handle_emergency_intervention(self, emergency_case):
        """Handle a specific emergency case"""
        try:
            user_id = emergency_case['user_id']
            action_needed = emergency_case['action_needed']
            
            if action_needed == 'TRANSPORT_AND_HEAL':
                # Transport then heal
                transport_success = await self.treatment.transport_to_hospital(user_id)
                if transport_success:
                    healing_success = await self.treatment.attempt_stabilization_healing(user_id)
                    return {'transport': transport_success, 'healing': healing_success}
                else:
                    return {'transport': False, 'healing': False}
                    
            elif action_needed == 'TRANSPORT_ONLY':
                # Transport only
                transport_success = await self.treatment.transport_to_hospital(user_id)
                return {'transport': transport_success, 'healing': None}
                
            elif action_needed == 'HEAL':
                # Heal only (already in hospital)
                healing_success = await self.treatment.attempt_stabilization_healing(user_id)
                return {'transport': None, 'healing': healing_success}
                
            elif action_needed == 'MONITOR':
                # Just monitor, no action possible
                return {'transport': None, 'healing': None, 'status': 'MONITORING'}
                
            elif action_needed == 'WAIT_FOR_COMBAT_END':
                # Cannot act while in combat
                return {'transport': None, 'healing': None, 'status': 'BLOCKED_BY_COMBAT'}
            
            return {'error': f'Unknown action: {action_needed}'}
            
        except Exception as e:
            logging.error(f"❌ Emergency intervention failed: {e}")
            return {'error': str(e)}