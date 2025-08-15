import discord
import logging
from datetime import datetime

TRANSPORT_COST = 1000  # Cost in shekels for hospital transport


class HospitalTransport:
    """Hospital emergency transport service - handles ambulance operations"""
    
    def __init__(self, hospital_core, hospital_financial):
        self.core = hospital_core
        self.financial = hospital_financial
    
    async def transport_to_hospital(self, user_id):
        """Attempt to transport unconscious user to hospital"""
        user = self.core.bot.get_user(user_id)
        if not user:
            await self.core.send_error_to_health_log(
                f"Cannot find user with ID {user_id} for transport",
                "User object not available"
            )
            return False
        
        # Check if user is in combat (can't transport during combat)
        if self.core.is_user_in_combat(user_id):
            await self.core.send_warning_to_health_log(
                f"Transport blocked for **{user.display_name}** - user is in combat",
                "Emergency transport cannot occur during active combat"
            )
            
            self.core.log_hospital_action(
                user_id, user.display_name, "TRANSPORT_FAILED", 
                cost=TRANSPORT_COST, success=False,
                details="User in combat - cannot transport"
            )
            return False
        
        # Check if already in hospital
        if self.core.is_in_hospital(user_id):
            await self.core.send_warning_to_health_log(
                f"Transport request for **{user.display_name}** denied - already in hospital",
                "User is already receiving medical care"
            )
            return False
        
        # Get current health for logging
        stats_core = self.core.get_stats_core()
        current_health = 0
        if stats_core:
            stats = stats_core.get_user_stats(user_id)
            if stats:
                current_health = stats['health']
        
        await self.core.send_text_to_health_log(
            f"Initiating emergency transport for **{user.display_name}** ({current_health} HP)",
            "🚑 Emergency Transport Initiated"
        )
        
        # Attempt to charge for transport
        success, method, cost = self.financial.charge_for_service(user, TRANSPORT_COST, "transport")
        
        if success:
            # Transport successful - set hospital status
            self.core.set_hospital_status(user_id, True)
            
            # Log the action
            self.core.log_hospital_action(
                user_id, user.display_name, "TRANSPORT", 
                cost=cost, payment_method=method, success=True,
                health_before=current_health, health_after=current_health,
                details=f"Emergency transport from {current_health} HP"
            )
            
            # Create detailed embed
            embed = discord.Embed(
                title="🚑 Emergency Transport",
                description=f"**{user.display_name}** has been transported to the hospital!",
                color=0xff6b6b
            )
            
            embed.add_field(
                name="🩺 Patient Status",
                value=f"Health: {current_health} HP (Unconscious)",
                inline=True
            )
            
            embed.add_field(
                name="💰 Transport Cost",
                value=f"₪{TRANSPORT_COST:,}",
                inline=True
            )
            
            embed.add_field(
                name="💳 Payment Method",
                value=method.title(),
                inline=True
            )
            
            embed.set_footer(text="Emergency medical transport • No taxes applied • Automatic healing will begin")
            
            await self.core.send_to_health_log(embed)
            
            # Also send success message
            await self.core.send_info_to_health_log(
                f"**{user.display_name}** successfully transported to hospital for ₪{cost:,} via {method}",
                "✅ Transport Successful"
            )
            
            logging.info(f"✅ Transported {user.display_name} to hospital for ₪{cost} ({method})")
            return True
        
        else:
            # Transport failed - log the failure
            self.core.log_hospital_action(
                user_id, user.display_name, "TRANSPORT_FAILED", 
                cost=TRANSPORT_COST, payment_method=method, success=False,
                health_before=current_health, health_after=current_health,
                details=f"Payment failed: {method}"
            )
            
            await self.core.send_error_to_health_log(
                f"Emergency transport failed for **{user.display_name}** - {method}",
                f"Patient remains unconscious with {current_health} HP. Transport cost: ₪{TRANSPORT_COST:,}"
            )
            
            logging.warning(f"❌ Failed to transport {user.display_name} to hospital: {method}")
            return False