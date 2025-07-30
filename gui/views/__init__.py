"""
GUI Views Package

Contains all the view modules for the Modern GUI Control Center.
"""

from .dashboard import DashboardView
from .task_management import TaskManagementView  
from .agent_control import AgentControlView
from .memory_intelligence import MemoryIntelligenceView
from .monitoring import MonitoringView
from .automation_control import AutomationControlView

__all__ = [
    "DashboardView",
    "TaskManagementView", 
    "AgentControlView",
    "MemoryIntelligenceView",
    "MonitoringView",
    "AutomationControlView"
]
