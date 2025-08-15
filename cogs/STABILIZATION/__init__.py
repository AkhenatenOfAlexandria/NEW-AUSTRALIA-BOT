"""
Stabilization System Package

A modular stabilization system for D&D-style Discord bots.
Handles unconsciousness, stabilization rolls, and natural recovery.

Usage:
    from STABILIZATION_SYSTEM import StabilizationCog

Components:
    - StabilizationCog: Main Discord cog with slash commands
    - StabilizationManager: Coordinates all system components  
    - StabilizationProcessor: Core business logic
    - StabilizationDatabase: Database operations
    - StabilizationLogger: Discord embed creation and logging
    - StabilizationTasks: Background task management
    - StabilizationRoller: Dice rolling mechanics
"""

from .STABILIZATION_MANAGER import StabilizationManager
from .STABILIZATION_PROCESSOR import StabilizationProcessor
from .STABILIZATION_DATABASE import StabilizationDatabase
from .STABILIZATION_LOGGER import StabilizationLogger
from .STABILIZATION_TASKS import StabilizationTasks
from .STABILIZATION_ROLLER import StabilizationRoller

__all__ = [
    'StabilizationCog',
    'StabilizationManager', 
    'StabilizationProcessor',
    'StabilizationDatabase',
    'StabilizationLogger',
    'StabilizationTasks',
    'StabilizationRoller'
]