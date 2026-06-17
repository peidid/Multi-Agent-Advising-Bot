"""
Collaborative Planning Mode

This module implements the multi-round negotiation workflow where:
1. Planning Agent proposes a course plan (JSON)
2. Programs, Courses, Policy agents critique in PARALLEL
3. Planning Agent revises based on feedback
4. Repeat until consensus or max rounds (5)
"""

from planning.schema import (
    SemesterPlan,
    CoursePlanJSON,
    AgentCritique,
    PlanningRound,
    PlanningSession
)
from planning.coordinator import PlanningModeCoordinator

__all__ = [
    'SemesterPlan',
    'CoursePlanJSON',
    'AgentCritique',
    'PlanningRound',
    'PlanningSession',
    'PlanningModeCoordinator'
]
