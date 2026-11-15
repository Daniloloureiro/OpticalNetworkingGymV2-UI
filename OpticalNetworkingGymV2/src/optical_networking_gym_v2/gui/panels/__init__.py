"""Painéis (abas) da interface gráfica."""

from .scenario_panel import ScenarioPanel
from .physics_panel import PhysicsPanel
from .traffic_panel import TrafficPanel
from .qot_panel import QoTPanel
from .heuristics_panel import HeuristicsPanel
from .execution_panel import ExecutionPanel
from .results_panel import ResultsPanel

__all__ = [
    "ScenarioPanel",
    "PhysicsPanel",
    "TrafficPanel",
    "QoTPanel",
    "HeuristicsPanel",
    "ExecutionPanel",
    "ResultsPanel",
]
