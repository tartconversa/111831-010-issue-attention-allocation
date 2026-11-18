"""按议题整理信号支撑与覆盖范围。

议题档案回答两个问题：这个候选议题有哪些信号支撑？每个信号
各自覆盖到哪些来源与地区？它只做分组汇总，不做取舍判断。
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class SignalSummary:
    """某一议题在单一信号下的支撑情况。"""

    signal: str
    total: float
    observations: int
    source_ids: tuple
    regions: tuple
    first_observed: str
    last_observed: str


@dataclass(frozen=True)
class TopicDossier:
    """一个候选议题的信号档案。"""

    topic: str
    signals: tuple
    observations: int
    source_ids: tuple
    regions: tuple

    @property
    def signal_names(self):
        return tuple(summary.signal for summary in self.signals)

    def signal_total(self, signal):
        """该议题在指定信号下的总量；无数据时返回 None（区别于 0）。"""
        for summary in self.signals:
            if summary.signal == signal:
                return summary.total
        return None


def build_dossiers(observations):
    """把观察记录按议题与信号分组，生成议题档案元组（按议题名排序）。"""
    grouped = {}
    for observation in observations:
        grouped.setdefault(observation.topic, {}).setdefault(
            observation.signal, []
        ).append(observation)

    dossiers = []
    for topic, by_signal in grouped.items():
        summaries = []
        for signal, rows in by_signal.items():
            summaries.append(SignalSummary(
                signal=signal,
                total=sum(row.value for row in rows),
                observations=len(rows),
                source_ids=tuple(sorted({row.source_id for row in rows})),
                regions=tuple(sorted({row.region for row in rows})),
                first_observed=min(row.observed_on for row in rows).isoformat(),
                last_observed=max(row.observed_on for row in rows).isoformat(),
            ))
        summaries.sort(key=lambda summary: summary.signal)
        all_rows = [row for rows in by_signal.values() for row in rows]
        dossiers.append(TopicDossier(
            topic=topic,
            signals=tuple(summaries),
            observations=len(all_rows),
            source_ids=tuple(sorted({row.source_id for row in all_rows})),
            regions=tuple(sorted({row.region for row in all_rows})),
        ))
    dossiers.sort(key=lambda dossier: dossier.topic)
    return tuple(dossiers)
