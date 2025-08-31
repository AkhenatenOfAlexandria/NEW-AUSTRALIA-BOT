import discord
from discord.ext import commands
import sqlite3
import logging
from datetime import datetime

from UTILS.CONFIGURATION import GUILD_ID
from SHEKELS.BALANCE import BALANCE
from SHEKELS.TRANSFERS import UPDATE_BALANCE, WITHDRAW

GUILD = discord.Object(id=GUILD_ID)
TRANSPORT_COST = 1000  # Cost in shekels for hospital transport
HEALING_COST_PER_HP = 1000   # Cost in shekels per HP healed


class HospitalCore:
    """Core hospital functionality - database operations and basic logic"""
    
    def __init__(self, bot):
        self.bot = bot
        self.init_database()
        
        # Initialize maintenance system
        try:
            from .HOSPITAL_MAINTENANCE import HospitalLogMaintenance
            self.maintenance = HospitalLogMaintenance()
        except ImportError:
            logging.warning("🏥 Hospital maintenance system not available")
            self.maintenance = None
    
    def init_database(self):
        """Initialize hospital location tracking database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Create hospital locations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hospital_locations (
                    user_id INTEGER PRIMARY KEY,
                    in_hospital BOOLEAN DEFAULT FALSE,
                    transport_time TIMESTAMP,
                    last_healing_attempt TIMESTAMP
                )
            ''')
            
            # Create hospital action log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS hospital_action_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action_type TEXT,
                    amount INTEGER,
                    cost INTEGER,
                    payment_method TEXT,
                    success BOOLEAN,
                    health_before INTEGER,
                    health_after INTEGER,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            ''')
            
            conn.commit()
            conn.close()
            logging.info("✅ Hospital database initialized successfully")
            
        except Exception as e:
            logging.error(f"❌ Failed to initialize hospital database: {e}")
    
    def is_in_hospital(self, user_id):
        """Check if user is currently in hospital"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('SELECT in_hospital FROM hospital_locations WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            conn.close()
            return result and result[0]
        except Exception as e:
            logging.error(f"❌ Failed to check hospital status: {e}")
            return False
    
    def set_hospital_status(self, user_id, in_hospital, transport_time=None):
        """Set user's hospital status"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            if transport_time is None:
                transport_time = datetime.now()
            
            cursor.execute('''
                INSERT OR REPLACE INTO hospital_locations 
                (user_id, in_hospital, transport_time) 
                VALUES (?, ?, ?)
            ''', (user_id, in_hospital, transport_time))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"❌ Failed to set hospital status: {e}")
            return False
    
    def update_healing_attempt(self, user_id):
        """Update the last healing attempt timestamp"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE hospital_locations 
                SET last_healing_attempt = ? 
                WHERE user_id = ?
            ''', (datetime.now(), user_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logging.error(f"❌ Failed to update healing attempt: {e}")
    
    def log_hospital_action(self, user_id, username, action_type, amount=0, cost=0, 
                           payment_method="", success=True, health_before=0, health_after=0, details=""):
        """Log hospital action to database (indefinitely by default)"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO hospital_action_log 
                (user_id, username, action_type, amount, cost, payment_method, 
                 success, health_before, health_after, details)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, username, action_type, amount, cost, payment_method, 
                  success, health_before, health_after, details))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logging.error(f"❌ Failed to log hospital action: {e}")
            return False
    
    def get_log_statistics(self):
        """Get hospital log statistics"""
        if self.maintenance:
            return self.maintenance.get_log_statistics()
        return None
    
    def perform_maintenance(self, force_backup=False):
        """Perform log maintenance (backup, optimization, etc.)"""
        if self.maintenance:
            return self.maintenance.perform_maintenance(force_backup)
        return False
    
    def get_stats_core(self):
        """Get the StatsCore cog for accessing core functionality"""
        return self.bot.get_cog('StatsCore')
    
    def get_combat_cog(self):
        """Get the StatsCombat cog to check combat status"""
        return self.bot.get_cog('StatsCombat')
    
    def is_user_in_combat(self, user_id):
        """Check if user is in combat"""
        combat_cog = self.get_combat_cog()
        if combat_cog and hasattr(combat_cog, 'is_user_in_combat'):
            return combat_cog.is_user_in_combat(user_id)
        return False
    
    async def get_health_log_channel(self):
        """Get the health log channel, fallback to money log if not available"""
        # Try to get HEALTH_LOG_ID from configuration first
        health_log_id = getattr(self.bot, 'HEALTH_LOG_ID', None)
        
        # Also try to import from configuration
        if not health_log_id:
            try:
                from UTILS.CONFIGURATION import HEALTH_LOG_ID
                health_log_id = HEALTH_LOG_ID
                logging.info(f"🏥 Found HEALTH_LOG_ID in configuration: {health_log_id}")
            except ImportError:
                logging.warning("❌ Could not import HEALTH_LOG_ID from configuration")
        
        if health_log_id:
            health_log = self.bot.get_channel(health_log_id)
            if health_log:
                logging.info(f"🏥 Using health log channel: {health_log.name} ({health_log_id})")
                return health_log
            else:
                logging.warning(f"❌ Health log channel {health_log_id} not found or bot cannot access it")
        
        # Fallback to money log
        money_log_id = getattr(self.bot, 'MONEY_LOG_ID', None)
        
        # Also try to import MONEY_LOG_ID from configuration
        if not money_log_id:
            try:
                from UTILS.CONFIGURATION import MONEY_LOG_ID
                money_log_id = MONEY_LOG_ID
                logging.info(f"🏥 Found MONEY_LOG_ID in configuration: {money_log_id}")
            except ImportError:
                logging.warning("❌ Could not import MONEY_LOG_ID from configuration")
        
        if money_log_id:
            money_log = self.bot.get_channel(money_log_id)
            if money_log:
                logging.info(f"🏥 Using money log channel as health log fallback: {money_log.name} ({money_log_id})")
                return money_log
            else:
                logging.warning(f"❌ Money log channel {money_log_id} not found or bot cannot access it")
        
        # If no log channels available, log to console
        logging.warning("❌ No health log or money log channel available for hospital system - using console only")
        return None
    
    async def send_to_health_log(self, embed):
        """Send embed to health log channel"""
        log_channel = await self.get_health_log_channel()
        if log_channel:
            try:
                await log_channel.send(embed=embed)
            except Exception as e:
                logging.error(f"❌ Failed to send to health log: {e}")
    
    async def send_text_to_health_log(self, message, title="🏥 Hospital System", color=0x3498db):
        """Send a text message to health log channel as an embed"""
        embed = discord.Embed(
            title=title,
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        await self.send_to_health_log(embed)
    
    async def send_error_to_health_log(self, error_message, details=""):
        """Send error message to health log channel"""
        embed = discord.Embed(
            title="❌ Hospital System Error",
            description=error_message,
            color=0xff0000,
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(
                name="📋 Details",
                value=details,
                inline=False
            )
        
        await self.send_to_health_log(embed)
    
    async def send_warning_to_health_log(self, warning_message, details=""):
        """Send warning message to health log channel"""
        embed = discord.Embed(
            title="⚠️ Hospital System Warning",
            description=warning_message,
            color=0xffa500,
            timestamp=datetime.now()
        )
        
        if details:
            embed.add_field(
                name="📋 Details",
                value=details,
                inline=False
            )
        
        await self.send_to_health_log(embed)
    
    async def send_info_to_health_log(self, info_message, title="ℹ️ Hospital System Info"):
        """Send info message to health log channel"""
        embed = discord.Embed(
            title=title,
            description=info_message,
            color=0x17a2b8,
            timestamp=datetime.now()
        )
        
        await self.send_to_health_log(embed)
    
    def heal_user(self, user_id, health_points):
        """Heal user by specified amount in the database"""
        try:
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            
            # Ensure parameters are the correct types
            user_id = int(user_id)  # Convert to int in case it's a string
            health_points = int(health_points)  # Ensure it's an integer
            
            # Get current health
            cursor.execute('SELECT health FROM user_stats WHERE user_id = ?', (user_id,))
            result = cursor.fetchone()
            if not result:
                conn.close()
                logging.error(f"❌ User {user_id} not found in user_stats table")
                return False
            
            current_health = int(result[0])  # Ensure current health is an integer
            new_health = current_health + health_points
            
            # Update with properly typed parameters
            cursor.execute('UPDATE user_stats SET health = ? WHERE user_id = ?', (new_health, user_id))
            
            # Verify the update was successful
            if cursor.rowcount == 0:
                conn.close()
                logging.error(f"❌ No rows updated when healing user {user_id}")
                return False
            
            conn.commit()
            conn.close()
            
            logging.info(f"✅ Healed user {user_id}: {current_health} → {new_health} HP (+{health_points})")
            return new_health
            
        except sqlite3.Error as e:
            logging.error(f"❌ SQLite error when healing user {user_id}: {e}")
            if 'conn' in locals():
                conn.close()
            return False
        except Exception as e:
            logging.error(f"❌ Failed to heal user {user_id}: {e}")
            if 'conn' in locals():
                conn.close()
            return False

    async def log_hospital_failures(self, failures_summary):
        """Send hospital failure summary to health log channel"""
        if not failures_summary:
            return
        
        # Create an embed for failures
        embed = discord.Embed(
            title="🏥 Hospital System - Action Failures",
            color=0xff6b6b,  # Red color for failures
            timestamp=datetime.now()
        )
        
        # Add transport failures
        if failures_summary.get('transport_failures'):
            transport_list = failures_summary['transport_failures']
            if len(transport_list) <= 10:
                failure_text = "\n".join([f"• {name}" for name in transport_list])
            else:
                failure_text = "\n".join([f"• {name}" for name in transport_list[:8]])
                failure_text += f"\n• ... and {len(transport_list) - 8} more"
            
            embed.add_field(
                name=f"🚑 Transport Failures ({len(transport_list)})",
                value=failure_text or "None",
                inline=False
            )
        
        # Add healing failures
        if failures_summary.get('healing_failures'):
            healing_list = failures_summary['healing_failures']
            if len(healing_list) <= 10:
                failure_text = "\n".join([f"• {name}" for name in healing_list])
            else:
                failure_text = "\n".join([f"• {name}" for name in healing_list[:8]])
                failure_text += f"\n... and {len(healing_list) - 8} more"
            
            embed.add_field(
                name=f"🩺 Healing Failures ({len(healing_list)})",
                value=failure_text or "None",
                inline=False
            )
        
        # Add summary info
        total_failures = len(failures_summary.get('transport_failures', [])) + len(failures_summary.get('healing_failures', []))
        embed.add_field(
            name="📊 Failure Summary",
            value=f"**Total Failures:** {total_failures}\n**Reason:** Insufficient funds",
            inline=False
        )
        
        embed.set_footer(text="Hospital System Cycle Complete")
        
        # Send to health log channel
        await self.send_to_health_log(embed)

    async def log_hospital_cycle_summary(self, cycle_stats):
        """Send complete hospital cycle summary to health log channel"""
        embed = discord.Embed(
            title="🏥 Hospital System Cycle Summary",
            color=0x4CAF50 if cycle_stats['total_actions'] > 0 else 0xFFC107,  # Green if actions, yellow if no actions
            timestamp=datetime.now()
        )
        
        # Add unconscious users count
        embed.add_field(
            name="💀 Unconscious Users Found",
            value=f"{cycle_stats.get('unconscious_count', 0)} users",
            inline=True
        )
        
        # Add successful actions
        embed.add_field(
            name="✅ Successful Actions",
            value=f"🚑 Transported: {cycle_stats.get('transported', 0)}\n🩺 Healed: {cycle_stats.get('healed_users', 0)} users ({cycle_stats.get('healing_sessions', 0)} sessions)\n🚪 Discharged: {cycle_stats.get('discharged', 0)}",
            inline=True
        )
        
        # Add financial info
        embed.add_field(
            name="💰 Financial",
            value=f"Total cost: ₪{cycle_stats.get('total_cost', 0)}",
            inline=True
        )
        
        # Add cycle info
        embed.add_field(
            name="⚡ Cycle Info",
            value=f"Duration: {cycle_stats.get('duration', 0):.2f}s\nTotal actions: {cycle_stats.get('total_actions', 0)}",
            inline=False
        )
        
        # Only mention failures briefly if there were any
        total_failures = len(cycle_stats.get('transport_failures', [])) + len(cycle_stats.get('healing_failures', []))
        if total_failures > 0:
            embed.add_field(
                name="❌ Failures",
                value=f"{total_failures} actions failed (insufficient funds)\nSee detailed failure log above.",
                inline=False
            )
        
        embed.set_footer(text="Next cycle in 5 minutes")
        
        # Send to health log channel
        await self.send_to_health_log(embed)