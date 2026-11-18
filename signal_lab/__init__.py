"""面向研究复核的数据观察与分析。"""

from .analysis import compare_periods
from .decisions import DecisionLedger, DecisionRecord, snapshot_hash
from .dossier import TopicDossier, build_dossiers
from .explain import explain_changes
from .ranking import Weighting, compare_weightings, rank_topics
from .records import Observation, Source
from .store import load_observations

__all__ = [
    "DecisionLedger",
    "DecisionRecord",
    "Observation",
    "Source",
    "TopicDossier",
    "Weighting",
    "build_dossiers",
    "compare_periods",
    "compare_weightings",
    "explain_changes",
    "load_observations",
    "rank_topics",
    "snapshot_hash",
]
