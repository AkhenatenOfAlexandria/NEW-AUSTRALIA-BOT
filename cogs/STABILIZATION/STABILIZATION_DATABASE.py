import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any

class StabilizationDatabase:
    """Handles all stabilization database operations"""
    
    def __init__(self, db_path: str = 'stats.db'):
        self.db_path = db_path
    
    def init_database(self):
        """Initialize database tables with proper schema"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create stabilization table if it doesn't exist
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS stabilization (
                        user_id INTEGER PRIMARY KEY,
                        is_unstable BOOLEAN DEFAULT FALSE,
                        successes INTEGER DEFAULT 0,
                        failures INTEGER DEFAULT 0,
                        next_roll_time TIMESTAMP,
                        last_recovery_time TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Create index for performance
                cursor.execute('''
                    CREATE INDEX IF NOT EXISTS idx_stabilization_next_roll 
                    ON stabilization(next_roll_time, is_unstable)
                ''')
                
                conn.commit()
                logging.info("✅ Stabilization database initialized")
                
        except Exception as e:
            logging.error(f"❌ Failed to initialize stabilization database: {e}")
            raise
    
    def get_stabilization_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user's current stabilization status"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, is_unstable, successes, failures, 
                           next_roll_time, last_recovery_time
                    FROM stabilization 
                    WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                if row:
                    result = dict(row)
                    # Convert timestamp strings back to datetime objects
                    if result['next_roll_time']:
                        result['next_roll_time'] = datetime.fromisoformat(result['next_roll_time'])
                    if result['last_recovery_time']:
                        result['last_recovery_time'] = datetime.fromisoformat(result['last_recovery_time'])
                    return result
                
                return None
                
        except Exception as e:
            logging.error(f"Error getting stabilization status for user {user_id}: {e}")
            return None
    
    def update_stabilization_status(self, user_id: int, **kwargs) -> bool:
        """Update user's stabilization status - FIXED to properly handle partial updates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # First, check if user exists and get current values
                cursor.execute('''
                    SELECT is_unstable, successes, failures, next_roll_time, last_recovery_time
                    FROM stabilization 
                    WHERE user_id = ?
                ''', (user_id,))
                
                existing_row = cursor.fetchone()
                
                if existing_row:
                    # User exists - update only the specified fields
                    current_values = {
                        'is_unstable': existing_row[0],
                        'successes': existing_row[1],
                        'failures': existing_row[2],
                        'next_roll_time': existing_row[3],
                        'last_recovery_time': existing_row[4]
                    }
                    
                    # Update with new values
                    for field, value in kwargs.items():
                        if field in current_values:
                            if isinstance(value, datetime):
                                current_values[field] = value.isoformat()
                            else:
                                current_values[field] = value
                    
                    # Update the existing row
                    cursor.execute('''
                        UPDATE stabilization 
                        SET is_unstable = ?, successes = ?, failures = ?, 
                            next_roll_time = ?, last_recovery_time = ?, updated_at = ?
                        WHERE user_id = ?
                    ''', (
                        current_values['is_unstable'],
                        current_values['successes'], 
                        current_values['failures'],
                        current_values['next_roll_time'],
                        current_values['last_recovery_time'],
                        datetime.now().isoformat(),
                        user_id
                    ))
                    
                    logging.debug(f"Updated existing stabilization record for user {user_id}: {kwargs}")
                    
                else:
                    # User doesn't exist - create new record with defaults
                    default_values = {
                        'is_unstable': False,
                        'successes': 0,
                        'failures': 0,
                        'next_roll_time': None,
                        'last_recovery_time': None
                    }
                    
                    # Override with provided values
                    for field, value in kwargs.items():
                        if field in default_values:
                            if isinstance(value, datetime):
                                default_values[field] = value.isoformat()
                            else:
                                default_values[field] = value
                    
                    # Insert new record
                    cursor.execute('''
                        INSERT INTO stabilization 
                        (user_id, is_unstable, successes, failures, next_roll_time, last_recovery_time, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id,
                        default_values['is_unstable'],
                        default_values['successes'],
                        default_values['failures'],
                        default_values['next_roll_time'],
                        default_values['last_recovery_time'],
                        datetime.now().isoformat(),
                        datetime.now().isoformat()
                    ))
                    
                    logging.debug(f"Created new stabilization record for user {user_id}: {kwargs}")
                
                conn.commit()
                return True
                
        except Exception as e:
            logging.error(f"Error updating stabilization status for user {user_id}: {e}")
            return False
    
    def get_pending_rolls(self, current_time: datetime) -> List[Dict[str, Any]]:
        """Get users who need stabilization rolls now - FIXED to use user_stats table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Modified query to use user_stats table instead of characters
                cursor.execute('''
                    SELECT s.user_id, s.successes, s.failures, s.next_roll_time,
                           COALESCE(us.health, 0) as current_health
                    FROM stabilization s
                    LEFT JOIN user_stats us ON s.user_id = us.user_id
                    WHERE s.is_unstable = TRUE 
                    AND s.next_roll_time <= ?
                ''', (current_time.isoformat(),))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result['next_roll_time']:
                        result['next_roll_time'] = datetime.fromisoformat(result['next_roll_time'])
                    results.append(result)
                
                # Debug logging
                if results:
                    logging.debug(f"Found {len(results)} users ready for stabilization rolls")
                    for result in results:
                        logging.debug(f"User {result['user_id']}: next_roll_time={result['next_roll_time']}, current_time={current_time}")
                
                return results
                
        except Exception as e:
            logging.error(f"Error getting pending rolls: {e}")
            return []
    
    def get_ready_for_recovery(self, current_time: datetime) -> List[Dict[str, Any]]:
        """Get users ready for natural recovery - FIXED to use user_stats table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Find users who are stable, at 0 HP, and haven't recovered in the last hour
                one_hour_ago = current_time - timedelta(hours=1)
                
                # Modified query to use user_stats table instead of characters
                cursor.execute('''
                    SELECT s.user_id, us.health as current_health
                    FROM stabilization s
                    LEFT JOIN user_stats us ON s.user_id = us.user_id
                    WHERE s.is_unstable = FALSE 
                    AND us.health = 0
                    AND (s.last_recovery_time IS NULL OR s.last_recovery_time <= ?)
                ''', (one_hour_ago.isoformat(),))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logging.error(f"Error getting users ready for recovery: {e}")
            return []
    
    def get_user_health(self, user_id: int) -> Optional[Dict[str, int]]:
        """Get user's current and max health"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Check what tables exist first
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cursor.fetchall()]
                logging.debug(f"Available tables: {tables}")
                
                # Try different possible table names/schemas
                possible_queries = [
                    # Option 1: user_stats table
                    "SELECT health as current_health, constitution, level FROM user_stats WHERE user_id = ?",
                    # Option 2: characters table  
                    "SELECT health as current_health, constitution, level FROM characters WHERE user_id = ?",
                    # Option 3: Simple health table
                    "SELECT health as current_health, 10 as constitution, 1 as level FROM user_health WHERE user_id = ?"
                ]
                
                for query in possible_queries:
                    try:
                        cursor.execute(query, (user_id,))
                        row = cursor.fetchone()
                        if row:
                            result = dict(row)
                            # Calculate max health (D&D 5e style)
                            constitution = result.get('constitution', 10)
                            level = result.get('level', 1)
                            con_modifier = (constitution - 10) // 2
                            max_health = max(level, 8 + con_modifier + (level - 1) * (5 + con_modifier))
                            
                            return {
                                'current_health': result['current_health'],
                                'max_health': max_health
                            }
                    except sqlite3.OperationalError as e:
                        logging.debug(f"Query failed: {query} - {e}")
                        continue
                
                logging.warning(f"No health data found for user {user_id} in any table")
                return None
                
        except Exception as e:
            logging.error(f"Error getting health for user {user_id}: {e}")
            return None
    
    def apply_health_change(self, user_id: int, health_change: int) -> Optional[int]:
        """Apply health change and return new health value - FIXED to use user_stats table"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current health first from user_stats table
                cursor.execute('SELECT health FROM user_stats WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                
                if not result:
                    logging.warning(f"No user stats found for user {user_id}")
                    return None
                
                current_health = result[0]
                new_health = current_health + health_change
                
                # Update health in user_stats table
                cursor.execute('''
                    UPDATE user_stats 
                    SET health = ? 
                    WHERE user_id = ?
                ''', (new_health, user_id))
                
                conn.commit()
                logging.debug(f"Applied health change for user {user_id}: {current_health} -> {new_health}")
                return new_health
                
        except Exception as e:
            logging.error(f"Error applying health change for user {user_id}: {e}")
            return None
    
    def clear_stabilization(self, user_id: int) -> bool:
        """Clear stabilization status (user is stable)"""
        return self.update_stabilization_status(
            user_id,
            is_unstable=False,
            successes=0,
            failures=0,
            next_roll_time=None
        )