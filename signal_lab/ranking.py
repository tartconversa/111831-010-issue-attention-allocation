"""覆盖感知的议题排序与多口径情景比较。

排序仅用于讨论资源安排：分数是按既定口径对已有信号的加权汇总，
不构成因果结论，也不代表唯一正确的顺序。缺失信号不按零分计——
它降低的是“支撑度”而不是分数；支撑度不足的议题列入“待补信息”，
而不是被当作低优先级排在末尾。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Weighting:
    """一套决策取舍：各信号的权重，以及纳入排序所需的最低支撑度。"""

    name: str
    weights: dict
    min_support: float = 0.5

    def __post_init__(self):
        if not self.weights:
            raise ValueError("weights 不能为空")
        if any(value < 0 for value in self.weights.values()):
            raise ValueError("权重不能为负")
        if sum(self.weights.values()) <= 0:
            raise ValueError("权重总和必须为正")
        if not 0 < self.min_support <= 1:
            raise ValueError("min_support 必须在 (0, 1] 之间")


@dataclass(frozen=True)
class RankedTopic:
    topic: str
    rank: int
    score: float
    support: float
    contributions: dict  # 信号 -> 权重×总量，用于解释分数构成


@dataclass(frozen=True)
class InsufficientTopic:
    """支撑度不足、暂不纳入排序的议题（待补信息，而非低优先级）。"""

    topic: str
    support: float
    missing_signals: tuple


@dataclass(frozen=True)
class Ranking:
    weighting: Weighting
    ranked: tuple
    insufficient: tuple


def rank_topics(dossiers, weighting, candidates=()):
    """按给定口径为议题打分排序。

    分数 = 已有信号的加权平均（Σ 权重×总量 ÷ 已有信号权重之和）；
    支撑度 = 已有信号的权重占全部权重之比。candidates 可列出暂无
    数据的候选议题，它们会以支撑度 0 进入待补信息，而不是从名单
    中消失。
    """
    dossier_map = {dossier.topic: dossier for dossier in dossiers}
    topics = sorted(set(dossier_map) | set(candidates))
    total_weight = sum(weighting.weights.values())

    scored = []
    insufficient = []
    for topic in topics:
        dossier = dossier_map.get(topic)
        contributions = {}
        available_weight = 0.0
        for signal, weight in weighting.weights.items():
            if weight == 0:
                continue
            value = dossier.signal_total(signal) if dossier else None
            if value is None:
                continue
            contributions[signal] = weight * value
            available_weight += weight
        support = available_weight / total_weight
        if support < weighting.min_support:
            missing = tuple(
                signal for signal, weight in weighting.weights.items()
                if weight > 0 and (dossier is None or dossier.signal_total(signal) is None)
            )
            insufficient.append(InsufficientTopic(topic, support, missing))
            continue
        score = sum(contributions.values()) / available_weight
        scored.append((topic, score, support, contributions))

    scored.sort(key=lambda item: (-item[1], item[0]))
    ranked = tuple(
        RankedTopic(topic, index + 1, score, support, contributions)
        for index, (topic, score, support, contributions) in enumerate(scored)
    )
    insufficient.sort(key=lambda entry: entry.topic)
    return Ranking(weighting, ranked, tuple(insufficient))


@dataclass(frozen=True)
class TopicMovement:
    """一个议题在各口径下的名次；None 表示该口径下为待补信息。"""

    topic: str
    ranks: dict  # 口径名 -> 名次或 None
    spread: object  # 有名次的口径之间的最大名次差；不足两个名次时为 None


@dataclass(frozen=True)
class ScenarioComparison:
    rankings: tuple
    movements: tuple


def compare_weightings(dossiers, weightings, candidates=()):
    """用多套口径分别排序，比较不同决策取舍对名次的影响。"""
    names = [weighting.name for weighting in weightings]
    if len(set(names)) != len(names):
        raise ValueError("口径名称不能重复")
    rankings = tuple(rank_topics(dossiers, weighting, candidates) for weighting in weightings)

    topics = sorted(
        {entry.topic for ranking in rankings for entry in ranking.ranked}
        | {entry.topic for ranking in rankings for entry in ranking.insufficient}
    )
    movements = []
    for topic in topics:
        ranks = {}
        for ranking in rankings:
            entry = next((e for e in ranking.ranked if e.topic == topic), None)
            ranks[ranking.weighting.name] = entry.rank if entry else None
        available = [rank for rank in ranks.values() if rank is not None]
        spread = max(available) - min(available) if len(available) > 1 else None
        movements.append(TopicMovement(topic, ranks, spread))
    movements.sort(key=lambda movement: (
        min((rank for rank in movement.ranks.values() if rank is not None),
            default=len(topics) + 1),
        movement.topic,
    ))
    return ScenarioComparison(rankings, tuple(movements))
