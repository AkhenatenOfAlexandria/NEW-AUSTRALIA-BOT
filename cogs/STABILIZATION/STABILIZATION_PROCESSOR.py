import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from .STABILIZATION_ROLLER import StabilizationRoller
from .STABILIZATION_DATABASE import StabilizationDatabase

class StabilizationProcessor:
    """Processes stabilization logic - coordinates roller and database"""
    
    def __init__(self):
        self.roller = StabilizationRoller()
        self.database = StabilizationDatabase()
    
    def start_stabilization(self, user_id: int) -> bool:
        """Start stabilization process for a user"""
        try:
            next_roll = datetime.now() + timedelta(seconds=6)
            success = self.database.update_stabilization_status(
                user_id,
                is_unstable=True,
                successes=0,
                failures=0,
                next_roll_time=next_roll
            )
            
            if success:
                logging.info(f"Started stabilization for user {user_id}")
            return success
            
        except Exception as e:
            logging.error(f"Error starting stabilization for user {user_id}: {e}")
            return False
    
    def process_stabilization_roll(self, user_id: int, current_health: int) -> Optional[Dict[str, Any]]:
        """Process a complete stabilization roll"""
        try:
            # Get current status
            status = self.database.get_stabilization_status(user_id)
            if not status or not status.get('is_unstable'):
                logging.warning(f"No unstable status found for user {user_id}")
                return None
            
            # Make the roll
            roll_result = self.roller.make_stabilization_roll(current_health)
            old_health = current_health
            
            # Apply health changes from special effects
            new_health = current_health
            if roll_result['health_change'] != 0:
                applied_health = self.database.apply_health_change(user_id, roll_result['health_change'])
                if applied_health is not None:
                    new_health = applied_health
            
            # Process the result based on success/failure
            process_result = self._process_roll_result(user_id, roll_result, status)
            
            return {
                'roll_result': roll_result,
                'process_result': process_result,
                'old_health': old_health,
                'new_health': new_health
            }
            
        except Exception as e:
            logging.error(f"Error processing stabilization roll for user {user_id}: {e}")
            return None
    
    def _process_roll_result(self, user_id: int, roll_result: Dict[str, Any], status: Dict[str, Any]) -> Dict[str, Any]:
        """Process roll result and update stabilization status - FIXED to restart on 3 failures"""
        try:
            current_successes = status.get('successes', 0)
            current_failures = status.get('failures', 0)
            
            if roll_result['success']:
                # Success - increment successes
                new_successes = current_successes + 1
                
                if new_successes >= 3:
                    # Stabilized! Clear stabilization status
                    self.database.clear_stabilization(user_id)
                    logging.info(f"User {user_id} has stabilized after {new_successes} successes")
                    return {
                        'result': 'stabilized',
                        'successes': new_successes,
                        'failures': current_failures
                    }
                else:
                    # Continue stabilizing - schedule next roll
                    next_roll = datetime.now() + timedelta(seconds=6)
                    success = self.database.update_stabilization_status(
                        user_id,
                        successes=new_successes,
                        failures=current_failures,  # Keep current failures
                        next_roll_time=next_roll
                    )
                    
                    if success:
                        logging.debug(f"User {user_id} stabilization continues: {new_successes}/3 successes, next roll in 6 seconds")
                    else:
                        logging.error(f"Failed to update stabilization status for user {user_id}")
                    
                    return {
                        'result': 'success',
                        'successes': new_successes,
                        'failures': current_failures
                    }
            else:
                # Failure - increment failures
                new_failures = current_failures + 1
                
                if new_failures >= 3:
                    # 3 failures! Lose 1 HP and restart stabilization
                    health_lost = self.database.apply_health_change(user_id, -1)
                    
                    if health_lost is not None:
                        # Reset stabilization counters and schedule next roll
                        next_roll = datetime.now() + timedelta(seconds=6)
                        success = self.database.update_stabilization_status(
                            user_id,
                            successes=0,  # Reset successes
                            failures=0,   # Reset failures
                            next_roll_time=next_roll
                        )
                        
                        if success:
                            logging.warning(f"User {user_id} lost 1 HP from 3 failures, restarting stabilization at {health_lost} HP")
                        else:
                            logging.error(f"Failed to reset stabilization status for user {user_id}")
                        
                        return {
                            'result': 'three_failures_restart',
                            'successes': 0,
                            'failures': 0,
                            'health_lost': 1,
                            'new_health': health_lost
                        }
                    else:
                        # Failed to apply health change
                        logging.error(f"Failed to apply health change for user {user_id}")
                        return {'result': 'error'}
                else:
                    # Continue stabilizing - schedule next roll
                    next_roll = datetime.now() + timedelta(seconds=6)
                    success = self.database.update_stabilization_status(
                        user_id,
                        successes=current_successes,  # Keep current successes
                        failures=new_failures,
                        next_roll_time=next_roll
                    )
                    
                    if success:
                        logging.debug(f"User {user_id} stabilization continues: {current_successes}/3 successes, {new_failures}/3 failures, next roll in 6 seconds")
                    else:
                        logging.error(f"Failed to update stabilization status for user {user_id}")
                    
                    return {
                        'result': 'failure',
                        'successes': current_successes,
                        'failures': new_failures
                    }
                    
        except Exception as e:
            logging.error(f"Error processing roll result for user {user_id}: {e}")
            return {'result': 'error'}
        
    def add_stabilization_failure(self, user_id: int, count: int = 1) -> str:
        """Add failures when user takes damage while stabilizing"""
        try:
            status = self.database.get_stabilization_status(user_id)
            if not status or not status.get('is_unstable'):
                # User not stabilizing, start stabilization instead
                self.start_stabilization(user_id)
                return 'started_stabilization'
            
            current_successes = status.get('successes', 0)
            current_failures = status.get('failures', 0)
            new_failures = current_failures + count
            
            if new_failures >= 3:
                # 3 failures! Lose 1 HP and restart stabilization
                health_lost = self.database.apply_health_change(user_id, -1)
                
                if health_lost is not None:
                    # Reset stabilization counters and schedule next roll
                    next_roll = datetime.now() + timedelta(seconds=6)
                    success = self.database.update_stabilization_status(
                        user_id,
                        successes=0,  # Reset successes
                        failures=0,   # Reset failures
                        next_roll_time=next_roll
                    )
                    
                    if success:
                        logging.warning(f"User {user_id} lost 1 HP from {new_failures} failures, restarting stabilization at {health_lost} HP")
                    else:
                        logging.error(f"Failed to reset stabilization status for user {user_id}")
                    
                    return 'three_failures_restart'
                else:
                    # Failed to apply health change
                    logging.error(f"Failed to apply health change for user {user_id}")
                    return 'error'
            else:
                # Update failures and continue - schedule next roll
                next_roll = datetime.now() + timedelta(seconds=6)
                success = self.database.update_stabilization_status(
                    user_id,
                    successes=current_successes,
                    failures=new_failures,
                    next_roll_time=next_roll
                )
                
                if success:
                    logging.info(f"Added {count} stabilization failures for user {user_id} (total: {new_failures}/3)")
                else:
                    logging.error(f"Failed to update stabilization failures for user {user_id}")
                
                return 'failure_added'
                
        except Exception as e:
            logging.error(f"Error adding stabilization failure for user {user_id}: {e}")
            return 'error'
    
    def process_recovery(self, user_id: int) -> Optional[int]:
        """Process natural recovery for a stabilized user at 0 HP"""
        try:
            health_data = self.database.get_user_health(user_id)
            if not health_data or health_data['current_health'] != 0:
                return None
            
            # Heal 1 HP
            new_health = self.database.apply_health_change(user_id, 1)
            
            if new_health is not None:
                # Update recovery timestamp
                self.database.update_stabilization_status(
                    user_id,
                    last_recovery_time=datetime.now()
                )
                logging.info(f"User {user_id} naturally recovered to {new_health} HP")
            
            return new_health
            
        except Exception as e:
            logging.error(f"Error processing recovery for user {user_id}: {e}")
            return None
    
    def is_user_stabilizing(self, user_id: int) -> bool:
        """Check if user is currently in stabilization"""
        try:
            status = self.database.get_stabilization_status(user_id)
            return status and status.get('is_unstable', False)
        except Exception as e:
            logging.error(f"Error checking stabilization status for user {user_id}: {e}")
            return False
    
    def get_stabilization_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get stabilization status for a user"""
        return self.database.get_stabilization_status(user_id)