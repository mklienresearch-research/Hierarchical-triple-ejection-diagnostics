"""v2: causal early-warning diagnostics for few-body disruption.

Core = hierarchical triples (IAS15). Flagship application = binary-single encounters.
"""
from .core import TripleConfig, simulate_triple, triple_outcome_counts
from .encounters import EncounterConfig, simulate_encounter, encounter_outcome_counts
from .features import FEATURE_NAMES, extract_window_features, full_trajectory_features
from .causal import run_causal_experiment

__all__ = [
    "TripleConfig",
    "simulate_triple",
    "triple_outcome_counts",
    "EncounterConfig",
    "simulate_encounter",
    "encounter_outcome_counts",
    "FEATURE_NAMES",
    "extract_window_features",
    "full_trajectory_features",
    "run_causal_experiment",
]
