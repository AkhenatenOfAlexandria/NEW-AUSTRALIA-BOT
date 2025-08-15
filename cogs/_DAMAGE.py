import sqlite3
import logging

def apply_damage(user_id, damage):
        """Apply damage to a user and update their health in the database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Get current health
            cursor.execute('SELECT health FROM user_stats WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            if not result:
                return False
            
            current_health = result[0]
            new_health = current_health - damage
            
            # Update health (can go negative)
            cursor.execute('UPDATE user_stats SET health = ? WHERE user_id = ?', (new_health, user_id))
            conn.commit()
            conn.close()
            
            return new_health
            
        except Exception as e:
            logging.error(f"❌ Failed to apply damage: {e}")
            return None