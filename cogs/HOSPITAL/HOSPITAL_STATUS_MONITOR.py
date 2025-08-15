import sqlite3
import logging
from datetime import datetime

class HospitalStatusMonitor:
    """Monitors and reports hospital system status"""
    
    def __init__(self, hospital_core, hospital_treatment):
        self.core = hospital_core
        self.treatment = hospital_treatment
    
    async def get_current_status(self):
        """Get comprehensive status report"""
        try:
            stats_core = self.core.get_stats_core()
            if not stats_core:
                return None
            
            status = {
                'total_users': 0,
                'unconscious_users': 0,
                'users_in_hospital': 0,
                'users_in_combat': 0,
                'conscious_in_hospital': 0,
                'unconscious_outside_hospital': 0,
                'unconscious_in_combat': 0,
                'system_healthy': True,
                'timestamp': datetime.now()
            }
            
            # Get all users with stats
            all_users = stats_core.get_all_users_with_stats()
            status['total_users'] = len(all_users)
            
            # Get users currently in hospital
            try:
                conn = sqlite3.connect('stats.db')
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM hospital_locations WHERE in_hospital = 1')
                hospital_users = [row[0] for row in cursor.fetchall()]
                conn.close()
                status['users_in_hospital'] = len(hospital_users)
            except Exception as e:
                logging.error(f"❌ Failed to get hospital users: {e}")
                status['system_healthy'] = False
            
            # Categorize all users
            for user_id in all_users:
                user_stats = stats_core.get_user_stats(user_id)
                if not user_stats:
                    continue
                
                current_health = user_stats['health']
                in_hospital = self.core.is_in_hospital(user_id)
                in_combat = self.core.is_user_in_combat(user_id)
                
                # Count unconscious users
                if current_health <= 0:
                    status['unconscious_users'] += 1
                    
                    if in_combat:
                        status['unconscious_in_combat'] += 1
                    elif not in_hospital:
                        status['unconscious_outside_hospital'] += 1
                
                # Count conscious users in hospital
                if current_health > 0 and in_hospital:
                    status['conscious_in_hospital'] += 1
                
                # Count users in combat
                if in_combat:
                    status['users_in_combat'] += 1
            
            # System health check
            if status['unconscious_outside_hospital'] > 0:
                status['system_healthy'] = False
            
            return status
            
        except Exception as e:
            logging.error(f"❌ Failed to get hospital status: {e}")
            return None
    
    async def get_user_categorization(self):
        """Categorize all users by status"""
        try:
            stats_core = self.core.get_stats_core()
            if not stats_core:
                return None
            
            categories = {
                'healthy_users': [],
                'unconscious_in_hospital': [],
                'unconscious_outside_hospital': [],
                'unconscious_in_combat': [],
                'conscious_in_hospital': [],
                'users_in_combat': [],
                'unknown_status': []
            }
            
            all_users = stats_core.get_all_users_with_stats()
            
            for user_id in all_users:
                user = self.core.bot.get_user(user_id)
                if not user:
                    continue
                
                user_stats = stats_core.get_user_stats(user_id)
                if not user_stats:
                    categories['unknown_status'].append({
                        'user_id': user_id,
                        'username': user.display_name,
                        'reason': 'No stats available'
                    })
                    continue
                
                current_health = user_stats['health']
                max_health = stats_core.calculate_health(user_stats['constitution'], user_stats['level'])
                in_hospital = self.core.is_in_hospital(user_id)
                in_combat = self.core.is_user_in_combat(user_id)
                
                user_data = {
                    'user_id': user_id,
                    'username': user.display_name,
                    'health': current_health,
                    'max_health': max_health,
                    'in_hospital': in_hospital,
                    'in_combat': in_combat
                }
                
                # Categorize user
                if current_health <= 0:
                    if in_combat:
                        categories['unconscious_in_combat'].append(user_data)
                    elif in_hospital:
                        categories['unconscious_in_hospital'].append(user_data)
                    else:
                        categories['unconscious_outside_hospital'].append(user_data)
                else:
                    if in_hospital:
                        categories['conscious_in_hospital'].append(user_data)
                    else:
                        categories['healthy_users'].append(user_data)
                
                if in_combat:
                    categories['users_in_combat'].append(user_data)
            
            return categories
            
        except Exception as e:
            logging.error(f"❌ Failed to categorize users: {e}")
            return None
    
    async def check_system_health(self):
        """Check if hospital system is functioning properly"""
        health_issues = []
        
        try:
            # Check if core components are available
            if not self.core:
                health_issues.append("Hospital core not available")
            
            if not self.treatment:
                health_issues.append("Hospital treatment not available")
            
            # Check if StatsCore is available
            stats_core = self.core.get_stats_core() if self.core else None
            if not stats_core:
                health_issues.append("StatsCore not available")
            
            # Check database connectivity
            try:
                conn = sqlite3.connect('stats.db')
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM hospital_locations')
                conn.close()
            except Exception as e:
                health_issues.append(f"Database connectivity issue: {str(e)}")
            
            # Check for unconscious users outside hospital
            status = await self.get_current_status()
            if status and status['unconscious_outside_hospital'] > 0:
                health_issues.append(f"{status['unconscious_outside_hospital']} unconscious users outside hospital")
            
            return {
                'healthy': len(health_issues) == 0,
                'issues': health_issues,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            logging.error(f"❌ Health check failed: {e}")
            return {
                'healthy': False,
                'issues': [f"Health check failed: {str(e)}"],
                'timestamp': datetime.now()
            }