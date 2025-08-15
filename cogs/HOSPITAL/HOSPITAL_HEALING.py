import discord
import logging
from datetime import datetime

HEALING_COST_PER_HP = 1000   # Cost in shekels per HP healed


class HospitalHealing:
    """Hospital medical treatment service - handles patient healing and stabilization"""
    
    def __init__(self, hospital_core, hospital_financial):
        self.core = hospital_core
        self.financial = hospital_financial
    
    async def attempt_stabilization_healing(self, user_id):
        """Attempt to heal user to stabilize (1 HP minimum) or until funds run out"""
        user = self.core.bot.get_user(user_id)
        if not user:
            await self.core.send_error_to_health_log(
                f"Cannot find user with ID {user_id} for healing",
                "User object not available"
            )
            return False
        
        # Must be in hospital
        if not self.core.is_in_hospital(user_id):
            await self.core.send_warning_to_health_log(
                f"Healing attempt for **{user.display_name}** denied - not in hospital",
                "Patient must be in hospital to receive treatment"
            )
            return False
        
        # Get current stats
        stats_core = self.core.get_stats_core()
        if not stats_core:
            await self.core.send_error_to_health_log(
                "Healing attempt failed - StatsCore system unavailable",
                f"Cannot access patient stats for {user.display_name}"
            )
            return False
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            await self.core.send_error_to_health_log(
                f"Healing attempt failed for **{user.display_name}** - no character stats",
                "Patient has no character statistics in system"
            )
            return False
        
        initial_health = stats['health']
        current_health = initial_health
        max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
        
        # If already conscious, no healing needed
        if current_health > 0:
            await self.core.send_warning_to_health_log(
                f"Healing not needed for **{user.display_name}** - patient is conscious ({current_health} HP)",
                "Patient does not require emergency medical intervention"
            )
            return False
        
        await self.core.send_text_to_health_log(
            f"Beginning stabilization healing for **{user.display_name}** ({current_health}/{max_health} HP) - target: 1 HP minimum",
            "🏥 Emergency Stabilization Started"
        )
        
        total_hp_healed = 0
        total_cost = 0
        healing_sessions = []
        session_count = 0
        
        # Keep healing until conscious (at least 1 HP) or can't afford more
        while current_health <= 0:
            session_count += 1
            
            # Calculate how much healing they need to reach 1 HP minimum
            hp_needed_to_stabilize = 1 - current_health  # e.g., if at -5 HP, need 6 HP to reach 1
            
            # Calculate how much healing they can afford
            affordable_hp, session_cost = self.financial.calculate_max_affordable_healing(user, current_health, max_health)
            
            # Limit healing to what's needed for stabilization (1 HP)
            if current_health < 0:
                # They're unconscious, prioritize getting to 1 HP
                healing_amount = min(affordable_hp, hp_needed_to_stabilize)
            else:
                # This shouldn't happen in this loop, but safety check
                healing_amount = affordable_hp
            
            if healing_amount <= 0:
                # Can't afford any more healing
                await self.core.send_warning_to_health_log(
                    f"Healing session {session_count} for **{user.display_name}** stopped - insufficient funds",
                    f"Cannot afford stabilization healing at ₪{HEALING_COST_PER_HP:,} per HP"
                )
                break
            
            # Recalculate cost based on actual healing amount
            actual_session_cost = healing_amount * HEALING_COST_PER_HP
            
            await self.core.send_text_to_health_log(
                f"Healing session {session_count} for **{user.display_name}**: attempting {healing_amount} HP for ₪{actual_session_cost:,} (stabilization priority)",
                f"🩺 Stabilization Session {session_count}"
            )
            
            # Attempt to charge for this healing session
            success, method, actual_cost = self.financial.charge_for_service(user, actual_session_cost, "healing")
            
            if success:
                # Apply healing
                new_health = self.core.heal_user(user_id, healing_amount)
                if new_health is False:
                    # Healing failed, refund
                    if method == "cash":
                        from SHEKELS.TRANSFERS import UPDATE_BALANCE
                        UPDATE_BALANCE(user, actual_cost, "CASH")
                    
                    await self.core.send_error_to_health_log(
                        f"Healing session {session_count} failed for **{user.display_name}** - database error (refunded)",
                        f"Failed to update health in database. ₪{actual_cost:,} refunded."
                    )
                    break
                
                # Log successful healing session
                self.core.log_hospital_action(
                    user_id, user.display_name, "HEALING", 
                    amount=healing_amount, cost=actual_cost, payment_method=method, success=True,
                    health_before=current_health, health_after=new_health,
                    details=f"Session {session_count} stabilization: {healing_amount} HP for ₪{actual_cost}"
                )
                
                healing_sessions.append({
                    'session': session_count,
                    'hp': healing_amount,
                    'cost': actual_cost,
                    'method': method,
                    'health_before': current_health,
                    'health_after': new_health
                })
                
                current_health = new_health
                total_hp_healed += healing_amount
                total_cost += actual_cost
                
                await self.core.send_info_to_health_log(
                    f"Session {session_count} successful: **{user.display_name}** healed +{healing_amount} HP for ₪{actual_cost:,} ({method}) → {new_health} HP",
                    "✅ Stabilization Session Complete"
                )
                
                logging.info(f"🩺 Healed {user.display_name}: +{healing_amount} HP for ₪{actual_cost} ({method}). Now at {new_health} HP")
                
                # If now conscious (1 HP or more), we can stop
                if current_health >= 1:
                    await self.core.send_info_to_health_log(
                        f"**{user.display_name}** is now stabilized at {current_health} HP! Emergency treatment complete after {session_count} sessions.",
                        "🎉 Patient Stabilized"
                    )
                    break
            
            else:
                # Payment failed
                self.core.log_hospital_action(
                    user_id, user.display_name, "HEALING_FAILED", 
                    amount=healing_amount, cost=actual_session_cost, payment_method=method, success=False,
                    health_before=current_health, health_after=current_health,
                    details=f"Session {session_count} payment failed: {method}"
                )
                
                await self.core.send_error_to_health_log(
                    f"Healing session {session_count} failed for **{user.display_name}** - payment failure ({method})",
                    f"Attempted to heal {healing_amount} HP for ₪{actual_session_cost:,} but payment failed"
                )
                break
        
        # Update healing attempt timestamp
        self.core.update_healing_attempt(user_id)
        
        # Send comprehensive healing summary if any healing occurred
        if healing_sessions:
            await self._send_healing_summary(user, initial_health, current_health, total_hp_healed, 
                                           total_cost, healing_sessions)
            
            logging.info(f"🏥 Hospital stabilization complete for {user.display_name}: {total_hp_healed} HP healed across {len(healing_sessions)} sessions for ₪{total_cost}")
            return True
        
        else:
            # No healing occurred
            await self.core.send_error_to_health_log(
                f"No healing provided to **{user.display_name}** in hospital - insufficient funds for any treatment",
                f"Patient remains at {current_health} HP. Minimum cost: ₪{HEALING_COST_PER_HP:,} per HP"
            )
            logging.warning(f"❌ No healing provided to {user.display_name} in hospital (insufficient funds)")
            return False
    
    async def _send_healing_summary(self, user, initial_health, current_health, total_hp_healed, 
                                   total_cost, healing_sessions):
        """Send comprehensive healing summary to health log"""
        embed = discord.Embed(
            title="🏥 Hospital Stabilization Complete",
            description=f"**{user.display_name}** has received emergency stabilization treatment!",
            color=0x2ecc71 if current_health >= 1 else 0xe67e22
        )
        
        # Summary of total treatment
        embed.add_field(
            name="🩺 Treatment Summary",
            value=f"Sessions: {len(healing_sessions)}\nTotal HP Restored: {total_hp_healed}\nHealth: {initial_health} → {current_health} HP\nTotal Cost: ₪{total_cost:,}",
            inline=False
        )
        
        # Status after treatment
        if current_health >= 1:
            embed.add_field(
                name="✅ Final Status",
                value="Patient stabilized and conscious",
                inline=True
            )
            embed.add_field(
                name="🚪 Discharge",
                value="Ready for discharge",
                inline=True
            )
        else:
            embed.add_field(
                name="🔴 Final Status",
                value=f"Still critical ({current_health} HP)",
                inline=True
            )
            embed.add_field(
                name="💰 Funding",
                value="Insufficient funds for stabilization",
                inline=True
            )
        
        # Detailed session breakdown if multiple sessions
        if len(healing_sessions) > 1:
            session_details = []
            for session in healing_sessions:
                session_details.append(
                    f"Session {session['session']}: +{session['hp']} HP for ₪{session['cost']:,} ({session['method']})"
                )
            
            embed.add_field(
                name="📋 Treatment Sessions",
                value="\n".join(session_details),
                inline=False
            )
        
        embed.add_field(
            name="ℹ️ Treatment Policy",
            value="Hospital provides emergency stabilization to 1 HP minimum. Additional healing available at patient request.",
            inline=False
        )
        
        embed.set_footer(text=f"Hospital provided {len(healing_sessions)} stabilization session(s) • No taxes applied")
        
        await self.core.send_to_health_log(embed)
        
        # Send final status message
        if current_health >= 1:
            await self.core.send_info_to_health_log(
                f"🎉 **{user.display_name}** stabilization successful: {total_hp_healed} HP restored across {len(healing_sessions)} sessions for ₪{total_cost:,}. Patient is now conscious and stabilized at {current_health} HP.",
                "✅ Stabilization Successful"
            )
        else:
            await self.core.send_warning_to_health_log(
                f"⚠️ **{user.display_name}** stabilization incomplete: {total_hp_healed} HP restored across {len(healing_sessions)} sessions for ₪{total_cost:,}. Patient remains critical due to insufficient funds.",
                "🔴 Stabilization Incomplete"
            )
    
    async def attempt_additional_healing(self, user_id, target_hp=None):
        """Attempt additional healing beyond stabilization (for conscious patients)"""
        # This could be used for future features like elective healing
        # For now, we focus on emergency stabilization only
        pass