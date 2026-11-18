"""面向研究复核的数据观察与分析。"""

from .analysis import compare_periods
from .records import Observation, Source

__all__ = ["Observation", "Source", "compare_periods"]
