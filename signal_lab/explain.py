"""比较两版观察数据，解释名次变化来自哪里。

归因只是讨论线索，帮助团队分辨名单翻转是否源于数据补齐：
- backfill（覆盖补齐）：变化主要来自新增来源或新地区的记录；
- signal-change（信号变化）：同一批来源/地区出现了新的观察值；
- revision（记录修正）：既有记录被改动；
- mixed / none：多种因素交织，或没有变化。

归因不证明因果；样本构成变化（例如某地区渠道补录）通常会表现
为 backfill。
"""

from dataclasses import dataclass

from .dossier import build_dossiers
from .ranking import rank_topics


@dataclass(frozen=True)
class TopicChange:
    topic: str
    old_rank: object  # None 表示旧版中为待补信息
    new_rank: object
    old_support: float
    new_support: float
    added_observations: int
    revised_observations: int
    removed_observations: int
    value_from_added: float      # 新增记录带来的数值（减去被移除的）
    value_from_revisions: float  # 既有记录被修正的数值差
    sources_added: tuple
    regions_added: tuple
    driver: str


def explain_changes(old_observations, new_observations, weighting, candidates=()):
    """用同一口径分别排序两版数据，逐议题解释名次与支撑度变化。"""
    old_by_id = {obs.observation_id: obs for obs in old_observations}
    new_by_id = {obs.observation_id: obs for obs in new_observations}
    topics = sorted(
        {obs.topic for obs in old_observations}
        | {obs.topic for obs in new_observations}
        | set(candidates)
    )
    old_ranking = rank_topics(build_dossiers(old_observations), weighting, topics)
    new_ranking = rank_topics(build_dossiers(new_observations), weighting, topics)

    def ranks_of(ranking):
        return {entry.topic: entry.rank for entry in ranking.ranked}

    def supports_of(ranking):
        supports = {entry.topic: entry.support for entry in ranking.ranked}
        supports.update({entry.topic: entry.support for entry in ranking.insufficient})
        return supports

    old_ranks, new_ranks = ranks_of(old_ranking), ranks_of(new_ranking)
    old_supports, new_supports = supports_of(old_ranking), supports_of(new_ranking)

    changes = []
    for topic in topics:
        old_rows = {i: o for i, o in old_by_id.items() if o.topic == topic}
        new_rows = {i: o for i, o in new_by_id.items() if o.topic == topic}
        added = [o for i, o in new_rows.items() if i not in old_rows]
        removed = [o for i, o in old_rows.items() if i not in new_rows]
        revised = [
            (old_rows[i], new_rows[i]) for i in old_rows.keys() & new_rows.keys()
            if old_rows[i] != new_rows[i]
        ]
        value_from_added = sum(o.value for o in added) - sum(o.value for o in removed)
        value_from_revisions = sum(new.value - old.value for old, new in revised)
        sources_added = tuple(sorted(
            {o.source_id for o in new_rows.values()}
            - {o.source_id for o in old_rows.values()}
        ))
        regions_added = tuple(sorted(
            {o.region for o in new_rows.values()}
            - {o.region for o in old_rows.values()}
        ))
        changes.append(TopicChange(
            topic=topic,
            old_rank=old_ranks.get(topic),
            new_rank=new_ranks.get(topic),
            old_support=old_supports.get(topic, 0.0),
            new_support=new_supports.get(topic, 0.0),
            added_observations=len(added),
            revised_observations=len(revised),
            removed_observations=len(removed),
            value_from_added=value_from_added,
            value_from_revisions=value_from_revisions,
            sources_added=sources_added,
            regions_added=regions_added,
            driver=_classify(added, removed, revised, sources_added, regions_added,
                             value_from_added, value_from_revisions),
        ))
    changes.sort(key=lambda change: (
        change.new_rank is None,
        change.new_rank if change.new_rank is not None else 0,
        change.topic,
    ))
    return tuple(changes)


def _classify(added, removed, revised, sources_added, regions_added,
              value_from_added, value_from_revisions):
    if not added and not removed and not revised:
        return "none"
    if revised and abs(value_from_revisions) >= abs(value_from_added):
        return "revision"
    if sources_added or regions_added:
        return "backfill"
    if added or removed:
        return "signal-change"
    return "mixed"
