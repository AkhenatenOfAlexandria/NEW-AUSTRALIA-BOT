import logging
import time
import sqlite3
from datetime import datetime, timedelta
from .HOSPITAL_CYCLE_LOGGER import HospitalCycleLogger

class HospitalCycleManager:
    """Manages the main hospital processing cycle"""
    
    def __init__(self, hospital_core, hospital_treatment):
        self.core = hospital_core
        self.treatment = hospital_treatment
        self.logger = HospitalCycleLogger(hospital_core)
    
    async def run_full_cycle(self):
        """Main cycle logic - Process all unconscious users"""
        cycle_start = time.time()
        cycle_stats = {
            'unconscious_count': 0,
            'transported': 0,
            'healed_users': 0,
            'healing_sessions': 0,
            'discharged': 0,
            'total_cost': 0,
            'total_actions': 0,
            'transport_failures': [],
            'healing_failures': [],
            'duration': 0
        }
        
        try:
            # Log cycle start
            await self.core.send_info_to_health_log(
                "Hospital cycle initiated - checking for unconscious users",
                "🔄 Hospital Cycle Started"
            )
            
            # Get StatsCore to check user health
            stats_core = self.core.get_stats_core()
            if not stats_core:
                await self.core.send_error_to_health_log(
                    "Hospital cycle aborted - StatsCore not available",
                    "Cannot access user health statistics"
                )
                return cycle_stats
            
            # Get all users with stats
            all_users = stats_core.get_all_users_with_stats()
            unconscious_users = []
            
            # Find unconscious users
            for user_id in all_users:
                stats = stats_core.get_user_stats(user_id)
                if stats and stats['health'] <= 0:
                    cycle_stats['unconscious_count'] += 1
                    user = self.core.bot.get_user(user_id)
                    if user:
                        unconscious_users.append((user_id, user, stats))
                        logging.info(f"🏥 Found unconscious user: {user.display_name} ({stats['health']} HP)")
            
            if not unconscious_users:
                await self.core.send_info_to_health_log(
                    "No unconscious users found - all patients are stable",
                    "✅ Hospital Cycle Complete"
                )
                cycle_stats['duration'] = time.time() - cycle_start
                return cycle_stats
            
            await self.core.send_info_to_health_log(
                f"Found {len(unconscious_users)} unconscious users requiring medical attention",
                f"🚨 Emergency Response Needed"
            )
            
            # Process each unconscious user
            for user_id, user, stats in unconscious_users:
                try:
                    result = await self._process_single_user(user_id, user, stats, cycle_stats)
                    cycle_stats.update(result)
                except Exception as e:
                    logging.error(f"❌ Error processing user {user.display_name}: {e}")
                    await self.core.send_error_to_health_log(
                        f"Error processing **{user.display_name}**: {str(e)}",
                        "Individual user processing failed"
                    )
            
            # Discharge conscious patients
            try:
                discharged_count, discharged_patients = await self.treatment.discharge_all_conscious_patients()
                cycle_stats['discharged'] = discharged_count
                cycle_stats['total_actions'] += discharged_count
                
                if discharged_count > 0:
                    await self.core.send_info_to_health_log(
                        f"Discharged {discharged_count} conscious patients: {', '.join(discharged_patients)}",
                        "🚪 Automatic Discharge Complete"
                    )
            except Exception as e:
                logging.error(f"❌ Error during discharge process: {e}")
                await self.core.send_error_to_health_log(
                    f"Error during discharge process: {str(e)}",
                    "Discharge process encountered an error"
                )
            
            # Calculate cycle duration
            cycle_stats['duration'] = time.time() - cycle_start
            
            # Log failures if any
            if cycle_stats['transport_failures'] or cycle_stats['healing_failures']:
                await self.core.log_hospital_failures({
                    'transport_failures': cycle_stats['transport_failures'],
                    'healing_failures': cycle_stats['healing_failures']
                })
            
            # Log cycle summary
            await self.core.log_hospital_cycle_summary(cycle_stats)
            
            logging.info(f"🏥 Hospital cycle complete: {cycle_stats['total_actions']} actions, {cycle_stats['duration']:.2f}s")
            
        except Exception as e:
            logging.error(f"❌ Hospital cycle failed: {e}")
            await self.core.send_error_to_health_log(
                f"Hospital cycle failed: {str(e)}",
                "Critical system error during hospital cycle"
            )
            cycle_stats['duration'] = time.time() - cycle_start
        
        return cycle_stats
    
    async def _process_single_user(self, user_id, user, stats, cycle_stats):
        """Process individual unconscious user"""
        result_stats = {
            'transported': 0,
            'healed_users': 0,
            'healing_sessions': 0,
            'total_cost': 0,
            'total_actions': 0
        }
        
        current_health = stats['health']
        in_hospital = self.core.is_in_hospital(user_id)
        in_combat = self.core.is_user_in_combat(user_id)
        
        logging.info(f"🏥 Processing {user.display_name}: {current_health} HP, in_hospital={in_hospital}, in_combat={in_combat}")
        
        # Step 1: Transport if needed and possible
        if not in_hospital and not in_combat:
            try:
                transport_success = await self.treatment.transport_to_hospital(user_id)
                if transport_success:
                    result_stats['transported'] = 1
                    result_stats['total_actions'] += 1
                    result_stats['total_cost'] += 1000  # TRANSPORT_COST
                    logging.info(f"✅ Transported {user.display_name} to hospital")
                else:
                    # Transport failed - add to failures
                    cycle_stats['transport_failures'].append(user.display_name)
                    logging.warning(f"❌ Failed to transport {user.display_name}")
                    return result_stats  # Can't proceed without transport
            except Exception as e:
                logging.error(f"❌ Transport error for {user.display_name}: {e}")
                cycle_stats['transport_failures'].append(user.display_name)
                return result_stats
        
        elif not in_hospital and in_combat:
            logging.info(f"⚔️ {user.display_name} is unconscious but in combat - cannot transport")
            return result_stats
        
        # Step 2: Heal if in hospital
        if self.core.is_in_hospital(user_id):
            try:
                # Count healing sessions in the last 5 minutes to track multiple sessions
                sessions_before = await self._count_recent_healing_sessions(user_id, datetime.now() - timedelta(minutes=5))
                
                healing_success = await self.treatment.attempt_stabilization_healing(user_id)
                
                if healing_success:
                    # Count sessions after healing to see how many were added
                    sessions_after = await self._count_recent_healing_sessions(user_id, datetime.now() - timedelta(minutes=5), include_cost=True)
                    
                    sessions_added = sessions_after['count'] - sessions_before
                    cost_added = sessions_after['cost']
                    
                    result_stats['healed_users'] = 1
                    result_stats['healing_sessions'] = sessions_added
                    result_stats['total_actions'] += sessions_added
                    result_stats['total_cost'] += cost_added
                    
                    logging.info(f"✅ Healed {user.display_name}: {sessions_added} sessions, ₪{cost_added}")
                else:
                    # Healing failed - add to failures
                    cycle_stats['healing_failures'].append(user.display_name)
                    logging.warning(f"❌ Failed to heal {user.display_name}")
            except Exception as e:
                logging.error(f"❌ Healing error for {user.display_name}: {e}")
                cycle_stats['healing_failures'].append(user.display_name)
        
        return result_stats
    
    async def _count_recent_healing_sessions(self, user_id, since_time, include_cost=False):
        """Count healing sessions for tracking"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            if include_cost:
                cursor.execute('''
                    SELECT COUNT(*), SUM(cost) 
                    FROM hospital_action_log 
                    WHERE user_id = ? AND action_type = "HEALING" AND success = 1 AND timestamp >= ?
                ''', (user_id, since_time))
                result = cursor.fetchone()
                conn.close()
                return {'count': result[0] if result[0] else 0, 'cost': result[1] if result[1] else 0}
            else:
                cursor.execute('''
                    SELECT COUNT(*) 
                    FROM hospital_action_log 
                    WHERE user_id = ? AND action_type = "HEALING" AND success = 1 AND timestamp >= ?
                ''', (user_id, since_time))
                result = cursor.fetchone()
                conn.close()
                return result[0] if result[0] else 0
        except Exception as e:
            logging.error(f"❌ Failed to count healing sessions: {e}")
            if include_cost:
                return {'count': 0, 'cost': 0}
            else:
                return 0