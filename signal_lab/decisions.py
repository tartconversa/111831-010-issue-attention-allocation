"""月度决定的留档与核验。

决定一经记录便不可改写：每条决定保存当时使用的观察数据快照
（含哈希）、口径（权重与支撑度阈值）、排序结果、选定议题与理由。
之后补录或修正数据时，用 recompute_pending 重算待决策名单；
已留档的决定只能通过 verify 核验，不会被悄悄更新。

verify 能发现留档文件内部的不一致（数据或结果被改动）；要防住
有意的整体替换，档案目录应置于版本控制或只读存储之下。
"""

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .dossier import build_dossiers
from .ranking import Weighting, rank_topics
from .store import observation_from_dict, observation_to_dict

_SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def snapshot_hash(observations):
    """观察数据快照的哈希，用于检测留档数据是否被改动。"""
    rows = sorted(
        (observation_to_dict(observation) for observation in observations),
        key=lambda row: row["observation_id"],
    )
    canonical = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class DecisionRecord:
    """一次留档的月度决定：数据快照、口径、结果与理由。"""

    decision_id: str
    period: str
    created_at: str
    weighting: Weighting
    candidates: tuple
    observations: tuple
    snapshot: str
    ranked: tuple        # 留档时的名次（dict 列表，便于 JSON 存档）
    insufficient: tuple  # 留档时的待补信息议题
    selected: tuple      # 负责人选定的议题
    rationale: str


@dataclass(frozen=True)
class Verification:
    decision_id: str
    ok: bool
    problems: tuple


class DecisionLedger:
    """附加式（append-only）的决定档案库：每个决定一个 JSON 文件，只增不改。"""

    def __init__(self, directory):
        self._dir = Path(directory)

    def path_for(self, decision_id):
        if not _SAFE_ID.match(decision_id):
            raise ValueError(f"decision_id 含非法字符：{decision_id!r}")
        return self._dir / f"{decision_id}.json"

    def record(self, decision_id, period, weighting, observations, selected,
               rationale, candidates=()):
        """留档一次决定；decision_id 已存在时拒绝写入（不覆盖历史）。"""
        observations = tuple(observations)
        ranking = rank_topics(build_dossiers(observations), weighting, candidates)
        record = DecisionRecord(
            decision_id=decision_id,
            period=period,
            created_at=datetime.now(timezone.utc).isoformat(),
            weighting=weighting,
            candidates=tuple(candidates),
            observations=observations,
            snapshot=snapshot_hash(observations),
            ranked=tuple(
                {"topic": entry.topic, "rank": entry.rank,
                 "score": entry.score, "support": entry.support}
                for entry in ranking.ranked
            ),
            insufficient=tuple(entry.topic for entry in ranking.insufficient),
            selected=tuple(selected),
            rationale=rationale,
        )
        path = self.path_for(decision_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:  # 已存在则失败，禁止覆盖
            json.dump(_record_to_dict(record), handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        return record

    def get(self, decision_id):
        path = self.path_for(decision_id)
        if not path.exists():
            raise KeyError(f"找不到决定：{decision_id}")
        return _record_from_dict(json.loads(path.read_text(encoding="utf-8")))

    def all(self):
        if not self._dir.exists():
            return []
        records = [
            _record_from_dict(json.loads(path.read_text(encoding="utf-8")))
            for path in sorted(self._dir.glob("*.json"))
        ]
        return sorted(records, key=lambda record: (record.created_at, record.decision_id))

    def verify(self, decision_id):
        """核验留档决定：快照未被改动，且结果仍由留档数据与口径推出。"""
        record = self.get(decision_id)
        problems = []
        if snapshot_hash(record.observations) != record.snapshot:
            problems.append("数据快照哈希不一致：留档数据可能被改动")
        recomputed = rank_topics(
            build_dossiers(record.observations), record.weighting, record.candidates
        )
        expected_ranked = tuple(
            {"topic": entry.topic, "rank": entry.rank,
             "score": entry.score, "support": entry.support}
            for entry in recomputed.ranked
        )
        if expected_ranked != record.ranked:
            problems.append("排序结果与留档数据和口径不一致")
        expected_insufficient = tuple(entry.topic for entry in recomputed.insufficient)
        if expected_insufficient != record.insufficient:
            problems.append("待补信息名单与留档数据和口径不一致")
        return Verification(decision_id, not problems, tuple(problems))

    def verify_all(self):
        return tuple(self.verify(record.decision_id) for record in self.all())

    def recompute_pending(self, observations, weighting=None, candidates=()):
        """用最近留档口径（或指定口径）重算待决策名单；不改动任何留档。"""
        if weighting is None:
            records = self.all()
            if not records:
                raise ValueError("档案库为空，需显式提供口径")
            weighting = records[-1].weighting
        return rank_topics(build_dossiers(observations), weighting, candidates)


def _weighting_to_dict(weighting):
    return {
        "name": weighting.name,
        "weights": dict(weighting.weights),
        "min_support": weighting.min_support,
    }


def _weighting_from_dict(data):
    return Weighting(
        name=data["name"],
        weights={key: float(value) for key, value in data["weights"].items()},
        min_support=float(data["min_support"]),
    )


def _record_to_dict(record):
    return {
        "decision_id": record.decision_id,
        "period": record.period,
        "created_at": record.created_at,
        "weighting": _weighting_to_dict(record.weighting),
        "candidates": list(record.candidates),
        "observations": [observation_to_dict(obs) for obs in record.observations],
        "snapshot": record.snapshot,
        "ranked": [dict(entry) for entry in record.ranked],
        "insufficient": list(record.insufficient),
        "selected": list(record.selected),
        "rationale": record.rationale,
    }


def _record_from_dict(data):
    return DecisionRecord(
        decision_id=data["decision_id"],
        period=data["period"],
        created_at=data["created_at"],
        weighting=_weighting_from_dict(data["weighting"]),
        candidates=tuple(data.get("candidates", ())),
        observations=tuple(observation_from_dict(row) for row in data["observations"]),
        snapshot=data["snapshot"],
        ranked=tuple(
            {"topic": entry["topic"], "rank": int(entry["rank"]),
             "score": float(entry["score"]), "support": float(entry["support"])}
            for entry in data["ranked"]
        ),
        insufficient=tuple(data["insufficient"]),
        selected=tuple(data["selected"]),
        rationale=data["rationale"],
    )
