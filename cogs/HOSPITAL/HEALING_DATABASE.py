# HEALING_DATABASE.py
import sqlite3
import logging
from datetime import datetime

class HealingDatabase:
    """Handles healing-related database operations"""
    
    def restore_health_to_database(self, user_id, new_health):
        """Update user's health in database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('UPDATE user_stats SET health = ? WHERE user_id = ?', 
                         (new_health, user_id))
            
            if cursor.rowcount == 0:
                conn.close()
                logging.warning(f"No user stats found for user {user_id}")
                return False
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to update health for user {user_id}: {e}")
            return False
    
    def log_healing_transaction(self, user_id, amount, cost, success):
        """Log healing transaction to database"""
        try:
            conn = sqlite3.connect('healing_logs.db')
            cursor = conn.cursor()
            
            # Create table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS healing_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    amount INTEGER NOT NULL,
                    cost INTEGER NOT NULL,
                    success BOOLEAN NOT NULL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                INSERT INTO healing_logs (user_id, amount, cost, success)
                VALUES (?, ?, ?, ?)
            ''', (user_id, amount, cost, success))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"Failed to log healing transaction: {e}")
            return False