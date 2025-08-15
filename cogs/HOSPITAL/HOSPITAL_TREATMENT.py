from .HOSPITAL_TRANSPORT import HospitalTransport
from .HOSPITAL_HEALING import HospitalHealing
from .HOSPITAL_DISCHARGE import HospitalDischarge


class HospitalTreatment:
    """
    Main hospital treatment coordinator - orchestrates transport, healing, and discharge services
    
    This class serves as the main interface for hospital treatment operations,
    delegating specific tasks to specialized service classes.
    """
    
    def __init__(self, hospital_core, hospital_financial):
        self.core = hospital_core
        self.financial = hospital_financial
        
        # Initialize specialized service components
        self.transport = HospitalTransport(hospital_core, hospital_financial)
        self.healing = HospitalHealing(hospital_core, hospital_financial)
        self.discharge = HospitalDischarge(hospital_core)
    
    # Transport operations (delegate to HospitalTransport)
    async def transport_to_hospital(self, user_id):
        """Transport unconscious user to hospital"""
        return await self.transport.transport_to_hospital(user_id)
    
    # Healing operations (delegate to HospitalHealing)
    async def attempt_maximum_healing(self, user_id):
        """Attempt to heal user to stabilization (1 HP minimum)"""
        return await self.healing.attempt_stabilization_healing(user_id)
    
    async def attempt_stabilization_healing(self, user_id):
        """Attempt stabilization healing (explicit method name)"""
        return await self.healing.attempt_stabilization_healing(user_id)
    
    # Discharge operations (delegate to HospitalDischarge)
    async def discharge_patient(self, user_id, discharge_type="AUTO", admin_user=None):
        """Discharge a patient from hospital"""
        return await self.discharge.discharge_patient(user_id, discharge_type, admin_user)
    
    async def can_discharge_safely(self, user_id):
        """Check if patient can be safely discharged"""
        return await self.discharge.can_discharge_safely(user_id)
    
    async def discharge_all_conscious_patients(self):
        """Discharge all conscious patients"""
        return await self.discharge.discharge_all_conscious_patients()
    
    # Comprehensive treatment operations
    async def provide_emergency_care(self, user_id):
        """
        Provide complete emergency care: transport if needed, then healing
        Returns: (transport_success, healing_success, final_status)
        """
        transport_success = False
        healing_success = False
        
        # Step 1: Transport if not in hospital
        if not self.core.is_in_hospital(user_id):
            transport_success = await self.transport_to_hospital(user_id)
            if not transport_success:
                return False, False, "TRANSPORT_FAILED"
        else:
            transport_success = True  # Already in hospital
        
        # Step 2: Provide healing if in hospital
        if self.core.is_in_hospital(user_id):
            healing_success = await self.healing.attempt_stabilization_healing(user_id)
            
            # Check final status
            stats_core = self.core.get_stats_core()
            if stats_core:
                stats = stats_core.get_user_stats(user_id)
                if stats:
                    final_health = stats['health']
                    if final_health >= 1:
                        return transport_success, healing_success, "STABILIZED"
                    elif healing_success:
                        return transport_success, healing_success, "PARTIAL_HEALING"
                    else:
                        return transport_success, healing_success, "INSUFFICIENT_FUNDS"
        
        return transport_success, healing_success, "UNKNOWN_STATUS"
    
    async def get_treatment_summary(self, user_id):
        """Get comprehensive treatment summary for a patient"""
        user = self.core.bot.get_user(user_id)
        if not user:
            return None
        
        stats_core = self.core.get_stats_core()
        if not stats_core:
            return None
        
        stats = stats_core.get_user_stats(user_id)
        if not stats:
            return None
        
        current_health = stats['health']
        max_health = stats_core.calculate_health(stats['constitution'], stats['level'])
        in_hospital = self.core.is_in_hospital(user_id)
        in_combat = self.core.is_user_in_combat(user_id)
        
        # Calculate treatment needs and costs
        treatment_summary = {
            'user_name': user.display_name,
            'current_health': current_health,
            'max_health': max_health,
            'in_hospital': in_hospital,
            'in_combat': in_combat,
            'is_conscious': current_health > 0,
            'needs_transport': current_health <= 0 and not in_hospital and not in_combat,
            'needs_healing': current_health <= 0 and in_hospital,
            'can_discharge': current_health > 0 and in_hospital,
            'blocked_by_combat': current_health <= 0 and in_combat
        }
        
        # Calculate costs if treatment is needed
        if treatment_summary['needs_transport']:
            treatment_summary['transport_cost'] = 1000  # TRANSPORT_COST
        
        if treatment_summary['needs_healing']:
            hp_needed = 1 - current_health
            affordable_hp, cost = self.financial.calculate_max_affordable_healing(user, current_health, max_health)
            treatment_summary['hp_needed_for_stabilization'] = hp_needed
            treatment_summary['affordable_hp'] = affordable_hp
            treatment_summary['estimated_healing_cost'] = cost
            treatment_summary['can_afford_stabilization'] = affordable_hp >= hp_needed
        
        return treatment_summary
    
    async def get_service_status(self):
        """Get status of all treatment services"""
        return {
            'transport_service': self.transport is not None,
            'healing_service': self.healing is not None,
            'discharge_service': self.discharge is not None,
            'core_systems': {
                'hospital_core': self.core is not None,
                'financial_system': self.financial is not None,
                'stats_core': self.core.get_stats_core() is not None if self.core else False,
                'combat_system': self.core.get_combat_cog() is not None if self.core else False
            }
        }