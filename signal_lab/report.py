from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AnalysisReport:
    report_id: str
    title: str
    period_start: str
    period_end: str
    source_ids: tuple[str, ...]
    measures: dict[str, float]
    created_at: str


def create_report(report_id, title, period_start, period_end, source_ids, measures):
    return AnalysisReport(
        report_id=report_id, title=title, period_start=period_start, period_end=period_end,
        source_ids=tuple(sorted(set(source_ids))), measures=dict(measures),
        created_at=datetime.now(timezone.utc).isoformat(),
    )
