import discord
import logging
from datetime import datetime


class HospitalDischarge:
    """Hospital patient discharge service - handles releasing patients from care"""
    
    def __init__(self, hospital_core):
        self.core = hospital_core
    
    async def discharge_patient(self, user_id, discharge_type="AUTO", admin_user=None):
        """Discharge a patient from the hospital"""
        user = self.core.bot.get_user(user_id)
        if not user:
            await self.core.send_error_to_health_log(
                f"Cannot find user with ID {user_id} for discharge",
                "User object not available"
            )
            return False
        
        if not self.core.is_in_hospital(user_id):
            await self.core.send_warning_to_health_log(
                f"Discharge request for **{user.display_name}** denied - not in hospital",
                "User is not currently a hospital patient"
            )
            return False
        
        # Get current health for logging
        current_health = 0
        stats_core = self.core.get_stats_core()
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                current_health = stats['health']
        
        # Set hospital status to false
        self.core.set_hospital_status(user_id, False)
        
        # Determine discharge details based on type
        discharge_details = self._get_discharge_details(discharge_type, admin_user)
        
        # Log the discharge
        self.core.log_hospital_action(
            user_id, user.display_name, discharge_details['action_type'],
            success=True, health_before=current_health, health_after=current_health,
            details=discharge_details['log_details']
        )
        
        # Create and send discharge notification
        await self._send_discharge_notification(user, current_health, discharge_details)
        
        # Send appropriate status message to health log
        await self._send_discharge_status_message(user, current_health, discharge_details)
        
        logging.info(f"🚪 {user.display_name} discharged from hospital ({discharge_type}: {current_health} HP)")
        return True
    
    def _get_discharge_details(self, discharge_type, admin_user=None):
        """Get discharge details based on discharge type"""
        if discharge_type == "ADMIN":
            return {
                'action_type': "ADMIN_DISCHARGE",
                'log_details': f"Force discharged by admin {admin_user.display_name if admin_user else 'Unknown'}",
                'title': "🔧 Administrative Discharge",
                'admin_info': f" by **{admin_user.display_name if admin_user else 'Unknown Admin'}**",
                'color': 0xff9500
            }
        elif discharge_type == "VOLUNTARY":
            return {
                'action_type': "VOLUNTARY_DISCHARGE",
                'log_details': "Player initiated discharge",
                'title': "🚪 Voluntary Discharge",
                'admin_info': "",
                'color': 0x2ecc71
            }
        else:  # AUTO
            return {
                'action_type': "DISCHARGE",
                'log_details': "Automatic discharge - patient conscious",
                'title': "✅ Automatic Discharge",
                'admin_info': "",
                'color': 0x2ecc71
            }
    
    async def _send_discharge_notification(self, user, current_health, discharge_details):
        """Send discharge notification embed to health log"""
        embed = discord.Embed(
            title=discharge_details['title'],
            description=f"**{user.display_name}** has been discharged from the hospital{discharge_details['admin_info']}",
            color=discharge_details['color'] if current_health > 0 else 0xff6b6b
        )
        
        embed.add_field(
            name="🩺 Patient Health",
            value=f"{current_health} HP",
            inline=True
        )
        
        embed.add_field(
            name="📋 Discharge Type",
            value=discharge_details['action_type'].replace('_', ' ').title(),
            inline=True
        )
        
        # Add warnings and special information
        if current_health <= 0:
            embed.add_field(
                name="⚠️ Warning",
                value="Patient is still unconscious and vulnerable",
                inline=False
            )
            embed.color = 0xff6b6b
        
        if discharge_details['action_type'] == "ADMIN_DISCHARGE":
            embed.add_field(
                name="🔧 Administrative Action",
                value="Use administrative discharges with caution",
                inline=False
            )
        
        if discharge_details['action_type'] == "VOLUNTARY_DISCHARGE" and current_health <= 10:
            embed.add_field(
                name="⚠️ Health Advisory",
                value="Patient discharged against medical advice with low health",
                inline=False
            )
        
        embed.set_footer(text="Hospital discharge complete")
        
        await self.core.send_to_health_log(embed)
    
    async def _send_discharge_status_message(self, user, current_health, discharge_details):
        """Send appropriate status message to health log based on discharge type"""
        if discharge_details['action_type'] == "ADMIN_DISCHARGE":
            await self.core.send_warning_to_health_log(
                f"**{user.display_name}** force-discharged from hospital by admin{discharge_details['admin_info']} (Health: {current_health} HP)",
                "Administrative override used"
            )
        elif discharge_details['action_type'] == "VOLUNTARY_DISCHARGE":
            await self.core.send_info_to_health_log(
                f"**{user.display_name}** voluntarily left the hospital (Health: {current_health} HP)",
                "Patient-initiated discharge"
            )
        else:
            await self.core.send_info_to_health_log(
                f"**{user.display_name}** automatically discharged from hospital (Health: {current_health} HP)",
                "Standard discharge procedure"
            )
    
    async def can_discharge_safely(self, user_id):
        """Check if a patient can be safely discharged"""
        stats_core = self.core.get_stats_core()
        if not stats_core:
            return False, "Cannot access patient stats"
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return False, "No user stats available"
        
        current_health = stats['health']
        
        if current_health <= 0:
            return False, f"Patient is unconscious ({current_health} HP)"
        elif current_health <= 5:
            return True, f"Discharge possible but patient has low health ({current_health} HP)"
        else:
            return True, f"Patient is stable for discharge ({current_health} HP)"
    
    async def discharge_all_conscious_patients(self):
        """Discharge all conscious patients (used by processor)"""
        discharged_count = 0
        discharged_patients = []
        
        try:
            import sqlite3
            conn = sqlite3.connect('stats.db')
            cursor = conn.cursor()
            cursor.execute('SELECT user_id FROM hospital_locations WHERE in_hospital = 1')
            hospital_patients = cursor.fetchall()
            conn.close()
            
            stats_core = self.core.get_stats_core()
            if not stats_core:
                return discharged_count, discharged_patients
            
            for (user_id,) in hospital_patients:
                stats = stats_core.get_user_stats(user_id)
                if stats and stats['health'] > 0:
                    user = self.core.bot.get_user(user_id)
                    if user:
                        success = await self.discharge_patient(user_id, "AUTO")
                        if success:
                            discharged_count += 1
                            discharged_patients.append(user.display_name)
            
        except Exception as e:
            logging.error(f"❌ Error in discharge_all_conscious_patients: {e}")
            await self.core.send_error_to_health_log(
                f"Error during automatic discharge of conscious patients: {str(e)}",
                "Automatic discharge process encountered an error"
            )
        
        return discharged_count, discharged_patients