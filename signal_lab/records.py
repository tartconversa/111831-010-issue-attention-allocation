from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Source:
    source_id: str
    region: str
    language: str
    active: bool = True


@dataclass(frozen=True)
class Observation:
    observation_id: str
    source_id: str
    observed_on: date
    topic: str
    value: float
    region: str = "global"
