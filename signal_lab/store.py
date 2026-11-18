"""观察记录的 JSON 读写。"""

import json
from datetime import date
from pathlib import Path

from .records import Observation


def load_observations(path):
    """从 JSON 文件读取观察记录；缺省字段按 records 的默认口径补齐。"""
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    return [observation_from_dict(row) for row in rows]


def observation_from_dict(row):
    return Observation(
        observation_id=row["observation_id"],
        source_id=row["source_id"],
        observed_on=date.fromisoformat(row["observed_on"]),
        topic=row["topic"],
        value=float(row["value"]),
        region=row.get("region", "global"),
        signal=row.get("signal", "reporting"),
    )


def observation_to_dict(observation):
    return {
        "observation_id": observation.observation_id,
        "source_id": observation.source_id,
        "observed_on": observation.observed_on.isoformat(),
        "topic": observation.topic,
        "value": float(observation.value),
        "region": observation.region,
        "signal": observation.signal,
    }
