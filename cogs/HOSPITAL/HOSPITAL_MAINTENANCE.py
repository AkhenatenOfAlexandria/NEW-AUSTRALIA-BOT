import sqlite3
import logging
import os
import shutil
from datetime import datetime, timedelta
from typing import Optional

# Import configuration (adjust path as needed)
try:
    from UTILS.CONFIGURATION import (
        HOSPITAL_LOG_RETENTION_DAYS,
        HOSPITAL_ENABLE_LOG_CLEANUP,
        HOSPITAL_LOG_CLEANUP_INTERVAL_DAYS,
        HOSPITAL_LOG_INDEX_OPTIMIZATION,
        HOSPITAL_ENABLE_LOG_BACKUP,
        HOSPITAL_BACKUP_INTERVAL_DAYS,
        HOSPITAL_BACKUP_LOCATION
    )
except ImportError:
    # Default values if not configured
    HOSPITAL_LOG_RETENTION_DAYS = None  # Indefinite retention
    HOSPITAL_ENABLE_LOG_CLEANUP = False
    HOSPITAL_LOG_CLEANUP_INTERVAL_DAYS = 7
    HOSPITAL_LOG_INDEX_OPTIMIZATION = True
    HOSPITAL_ENABLE_LOG_BACKUP = True
    HOSPITAL_BACKUP_INTERVAL_DAYS = 30
    HOSPITAL_BACKUP_LOCATION = "backups/hospital_logs/"


class HospitalLogMaintenance:
    """Hospital log maintenance system for indefinite retention and performance optimization"""
    
    def __init__(self):
        self.db_path = 'stats.db'
        self.backup_location = HOSPITAL_BACKUP_LOCATION
        self.last_cleanup = None
        self.last_backup = None
        self._ensure_backup_directory()
        
        if HOSPITAL_LOG_INDEX_OPTIMIZATION:
            self._create_performance_indexes()
    
    def _ensure_backup_directory(self):
        """Ensure backup directory exists"""
        if HOSPITAL_ENABLE_LOG_BACKUP:
            os.makedirs(self.backup_location, exist_ok=True)
    
    def _create_performance_indexes(self):
        """Create database indexes for better performance with large log tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Indexes for hospital_action_log table
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_hospital_log_user_id ON hospital_action_log(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_hospital_log_timestamp ON hospital_action_log(timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_hospital_log_action_type ON hospital_action_log(action_type)",
                "CREATE INDEX IF NOT EXISTS idx_hospital_log_success ON hospital_action_log(success)",
                "CREATE INDEX IF NOT EXISTS idx_hospital_log_user_timestamp ON hospital_action_log(user_id, timestamp)",
                "CREATE INDEX IF NOT EXISTS idx_hospital_log_type_timestamp ON hospital_action_log(action_type, timestamp)",
                
                # Indexes for hospital_locations table
                "CREATE INDEX IF NOT EXISTS idx_hospital_locations_status ON hospital_locations(in_hospital)",
                "CREATE INDEX IF NOT EXISTS idx_hospital_locations_transport_time ON hospital_locations(transport_time)",
            ]
            
            for index_sql in indexes:
                cursor.execute(index_sql)
            
            conn.commit()
            conn.close()
            logging.info("✅ Hospital database indexes created/verified for performance optimization")
            
        except Exception as e:
            logging.error(f"❌ Failed to create hospital database indexes: {e}")
    
    def get_log_statistics(self):
        """Get statistics about hospital logs"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Total log entries
            cursor.execute('SELECT COUNT(*) FROM hospital_action_log')
            total_logs = cursor.fetchone()[0]
            
            # Oldest log entry
            cursor.execute('SELECT MIN(timestamp) FROM hospital_action_log')
            oldest_log = cursor.fetchone()[0]
            
            # Newest log entry
            cursor.execute('SELECT MAX(timestamp) FROM hospital_action_log')
            newest_log = cursor.fetchone()[0]
            
            # Log size estimation (rough)
            cursor.execute("SELECT COUNT(*) * 200 as estimated_bytes FROM hospital_action_log")  # ~200 bytes per log entry
            estimated_size = cursor.fetchone()[0]
            
            # Action type breakdown
            cursor.execute('''
                SELECT action_type, COUNT(*) as count 
                FROM hospital_action_log 
                GROUP BY action_type 
                ORDER BY count DESC
            ''')
            action_breakdown = cursor.fetchall()
            
            # Recent activity (last 7 days)
            week_ago = datetime.now() - timedelta(days=7)
            cursor.execute('SELECT COUNT(*) FROM hospital_action_log WHERE timestamp >= ?', (week_ago,))
            recent_activity = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'total_logs': total_logs,
                'oldest_log': oldest_log,
                'newest_log': newest_log,
                'estimated_size_bytes': estimated_size,
                'estimated_size_mb': round(estimated_size / (1024 * 1024), 2),
                'action_breakdown': action_breakdown,
                'recent_activity_7d': recent_activity
            }
            
        except Exception as e:
            logging.error(f"❌ Failed to get log statistics: {e}")
            return None
    
    def cleanup_old_logs(self, days_to_keep: Optional[int] = None):
        """Clean up old logs if cleanup is enabled"""
        if not HOSPITAL_ENABLE_LOG_CLEANUP:
            logging.info("🏥 Log cleanup is disabled - keeping all logs indefinitely")
            return False
        
        days = days_to_keep or HOSPITAL_LOG_RETENTION_DAYS
        if not days:
            logging.info("🏥 No retention period set - keeping all logs indefinitely")
            return False
        
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Count logs to be deleted
            cursor.execute('SELECT COUNT(*) FROM hospital_action_log WHERE timestamp < ?', (cutoff_date,))
            logs_to_delete = cursor.fetchone()[0]
            
            if logs_to_delete == 0:
                logging.info("🏥 No old hospital logs to clean up")
                conn.close()
                return False
            
            # Delete old logs
            cursor.execute('DELETE FROM hospital_action_log WHERE timestamp < ?', (cutoff_date,))
            
            # Vacuum database to reclaim space
            cursor.execute('VACUUM')
            
            conn.commit()
            conn.close()
            
            self.last_cleanup = datetime.now()
            logging.info(f"🏥 Cleaned up {logs_to_delete} hospital log entries older than {days} days")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to cleanup old hospital logs: {e}")
            return False
    
    def backup_logs(self, force_backup: bool = False):
        """Create a backup of hospital logs"""
        if not HOSPITAL_ENABLE_LOG_BACKUP and not force_backup:
            logging.info("🏥 Log backup is disabled")
            return False
        
        # Check if backup is needed
        if not force_backup and self.last_backup:
            time_since_backup = datetime.now() - self.last_backup
            if time_since_backup.days < HOSPITAL_BACKUP_INTERVAL_DAYS:
                logging.info(f"🏥 Hospital log backup not needed (last backup {time_since_backup.days} days ago)")
                return False
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"hospital_logs_backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_location, backup_filename)
            
            # Create backup by copying the database
            shutil.copy2(self.db_path, backup_path)
            
            # Extract only hospital tables to a separate backup file
            hospital_backup_path = os.path.join(self.backup_location, f"hospital_only_backup_{timestamp}.db")
            
            # Create hospital-only backup
            source_conn = sqlite3.connect(self.db_path)
            backup_conn = sqlite3.connect(hospital_backup_path)
            
            # Copy hospital tables
            source_conn.execute("ATTACH DATABASE ? AS backup_db", (hospital_backup_path,))
            
            # Copy hospital_action_log table
            source_conn.execute('''
                CREATE TABLE backup_db.hospital_action_log AS 
                SELECT * FROM hospital_action_log
            ''')
            
            # Copy hospital_locations table
            source_conn.execute('''
                CREATE TABLE backup_db.hospital_locations AS 
                SELECT * FROM hospital_locations
            ''')
            
            source_conn.close()
            backup_conn.close()
            
            self.last_backup = datetime.now()
            
            # Get backup statistics
            backup_size = os.path.getsize(hospital_backup_path)
            backup_size_mb = round(backup_size / (1024 * 1024), 2)
            
            logging.info(f"✅ Hospital logs backed up to {hospital_backup_path} ({backup_size_mb} MB)")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to backup hospital logs: {e}")
            return False
    
    def optimize_database(self):
        """Optimize database performance for large log tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            logging.info("🏥 Starting hospital database optimization...")
            
            # Analyze tables for query optimization
            cursor.execute('ANALYZE hospital_action_log')
            cursor.execute('ANALYZE hospital_locations')
            
            # Update statistics
            cursor.execute('PRAGMA optimize')
            
            # Vacuum if needed (only if cleanup was performed)
            if self.last_cleanup:
                cursor.execute('VACUUM')
                logging.info("🏥 Database vacuumed to reclaim space")
            
            conn.commit()
            conn.close()
            
            logging.info("✅ Hospital database optimization completed")
            return True
            
        except Exception as e:
            logging.error(f"❌ Failed to optimize hospital database: {e}")
            return False
    
    def perform_maintenance(self, force_backup: bool = False):
        """Perform all maintenance tasks"""
        logging.info("🏥 Starting hospital log maintenance...")
        
        # Get current statistics
        stats = self.get_log_statistics()
        if stats:
            logging.info(f"🏥 Current log statistics: {stats['total_logs']} entries, "
                        f"{stats['estimated_size_mb']} MB estimated size")
        
        maintenance_performed = False
        
        # Backup logs
        if self.backup_logs(force_backup):
            maintenance_performed = True
        
        # Clean up old logs (only if enabled)
        if self.cleanup_old_logs():
            maintenance_performed = True
        
        # Optimize database
        if self.optimize_database():
            maintenance_performed = True
        
        if maintenance_performed:
            logging.info("✅ Hospital log maintenance completed")
        else:
            logging.info("🏥 No hospital log maintenance needed")
        
        return maintenance_performed
    
    def get_maintenance_status(self):
        """Get current maintenance status"""
        return {
            'retention_enabled': HOSPITAL_ENABLE_LOG_CLEANUP,
            'retention_days': HOSPITAL_LOG_RETENTION_DAYS,
            'backup_enabled': HOSPITAL_ENABLE_LOG_BACKUP,
            'backup_interval_days': HOSPITAL_BACKUP_INTERVAL_DAYS,
            'last_cleanup': self.last_cleanup,
            'last_backup': self.last_backup,
            'indexes_enabled': HOSPITAL_LOG_INDEX_OPTIMIZATION,
            'backup_location': self.backup_location
        }