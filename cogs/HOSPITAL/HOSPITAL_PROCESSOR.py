import logging
from .HOSPITAL_CYCLE_MANAGER import HospitalCycleManager
from .HOSPITAL_STATUS_MONITOR import HospitalStatusMonitor
from .HOSPITAL_EMERGENCY_CHECKER import HospitalEmergencyChecker

class HospitalProcessor:
    """Main hospital processor - delegates to specialized managers"""
    
    def __init__(self, hospital_core, hospital_treatment):
        self.core = hospital_core
        self.treatment = hospital_treatment
        
        # Initialize specialized managers
        self.cycle_manager = HospitalCycleManager(hospital_core, hospital_treatment)
        self.status_monitor = HospitalStatusMonitor(hospital_core, hospital_treatment)
        self.emergency_checker = HospitalEmergencyChecker(hospital_core, hospital_treatment)
    
    async def process_unconscious_users(self):
        """Main processing cycle - delegate to cycle manager"""
        return await self.cycle_manager.run_full_cycle()
    
    async def get_current_hospital_status(self):
        """Get hospital status - delegate to status monitor"""
        return await self.status_monitor.get_current_status()
    
    async def emergency_intervention_check(self):
        """Emergency check - delegate to emergency checker"""
        return await self.emergency_checker.check_for_emergencies()