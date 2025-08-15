# HOSPITAL_CYCLE_LOGGER.py - Complete Implementation
import discord
from datetime import datetime
import logging

class HospitalCycleLogger:
    """Handles all cycle logging and reporting"""
    
    def __init__(self, hospital_core):
        self.core = hospital_core
    
    async def log_cycle_start(self, cycle_start):
        """Log cycle initiation"""
        try:
            await self.core.send_info_to_health_log(
                f"Hospital processing cycle initiated at {cycle_start.strftime('%H:%M:%S')}",
                "🔄 Hospital Cycle Started"
            )
        except Exception as e:
            logging.error(f"❌ Failed to log cycle start: {e}")
    
    async def log_cycle_summary(self, cycle_stats):
        """Log comprehensive cycle results"""
        try:
            if cycle_stats['total_actions'] == 0:
                await self.core.send_info_to_health_log(
                    f"Hospital cycle complete - no actions required. Found {cycle_stats['unconscious_count']} unconscious users, all already receiving appropriate care.",
                    "✅ Hospital Cycle Complete"
                )
            else:
                summary = []
                
                if cycle_stats['transported'] > 0:
                    summary.append(f"🚑 {cycle_stats['transported']} transported")
                
                if cycle_stats['healed_users'] > 0:
                    summary.append(f"🩺 {cycle_stats['healed_users']} patients healed ({cycle_stats['healing_sessions']} sessions)")
                
                if cycle_stats['discharged'] > 0:
                    summary.append(f"🚪 {cycle_stats['discharged']} discharged")
                
                if cycle_stats['total_cost'] > 0:
                    summary.append(f"💰 Total cost: ₪{cycle_stats['total_cost']:,}")
                
                action_summary = ", ".join(summary) if summary else "No actions completed"
                
                await self.core.send_info_to_health_log(
                    f"Hospital cycle complete in {cycle_stats['duration']:.2f}s - {action_summary}",
                    "✅ Hospital Cycle Complete"
                )
                
        except Exception as e:
            logging.error(f"❌ Failed to log cycle summary: {e}")
    
    async def create_detailed_summary_embed(self, cycle_data):
        """Create Discord embed for detailed summary"""
        try:
            embed = discord.Embed(
                title="🏥 Hospital Cycle Detailed Summary",
                color=0x2ecc71 if cycle_data['total_actions'] > 0 else 0x95a5a6,
                timestamp=datetime.now()
            )
            
            # Overview
            embed.add_field(
                name="📊 Overview",
                value=f"Duration: {cycle_data['duration']:.2f}s\nTotal Actions: {cycle_data['total_actions']}\nUnconscious Found: {cycle_data['unconscious_count']}",
                inline=False
            )
            
            # Actions taken
            if cycle_data['total_actions'] > 0:
                actions_text = []
                if cycle_data['transported'] > 0:
                    actions_text.append(f"🚑 Transported: {cycle_data['transported']}")
                if cycle_data['healed_users'] > 0:
                    actions_text.append(f"🩺 Healed: {cycle_data['healed_users']} users ({cycle_data['healing_sessions']} sessions)")
                if cycle_data['discharged'] > 0:
                    actions_text.append(f"🚪 Discharged: {cycle_data['discharged']}")
                
                embed.add_field(
                    name="⚡ Actions Completed",
                    value="\n".join(actions_text) if actions_text else "None",
                    inline=True
                )
            
            # Financial summary
            if cycle_data['total_cost'] > 0:
                embed.add_field(
                    name="💰 Financial",
                    value=f"Total Cost: ₪{cycle_data['total_cost']:,}",
                    inline=True
                )
            
            # Failures
            total_failures = len(cycle_data.get('transport_failures', [])) + len(cycle_data.get('healing_failures', []))
            if total_failures > 0:
                embed.add_field(
                    name="❌ Failures",
                    value=f"Transport: {len(cycle_data.get('transport_failures', []))}\nHealing: {len(cycle_data.get('healing_failures', []))}",
                    inline=True
                )
            
            embed.set_footer(text="Hospital System - Comprehensive Emergency Medical Services")
            return embed
            
        except Exception as e:
            logging.error(f"❌ Failed to create detailed summary embed: {e}")
            return None

# ================================================================================
# HOSPITAL_CYCLE_MANAGER.py - Complete Implementation
# ================================================================================

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
            logging.info("🏥 Starting hospital cycle")
            
            # Log cycle start
            await self.logger.log_cycle_start(datetime.now())
            
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
                    # Merge result stats into cycle stats
                    cycle_stats['transported'] += result.get('transported', 0)
                    cycle_stats['healed_users'] += result.get('healed_users', 0)
                    cycle_stats['healing_sessions'] += result.get('healing_sessions', 0)
                    cycle_stats['total_cost'] += result.get('total_cost', 0)
                    cycle_stats['total_actions'] += result.get('total_actions', 0)
                    
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
            await self.logger.log_cycle_summary(cycle_stats)
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

# ================================================================================
# HOSPITAL_STATUS_MONITOR.py - Complete Implementation  
# ================================================================================

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

# ================================================================================
# HOSPITAL_EMERGENCY_CHECKER.py - Complete Implementation
# ================================================================================

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