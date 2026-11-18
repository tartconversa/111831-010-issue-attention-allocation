"""分析输出：报告对象与决策支持报告的渲染。"""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class AnalysisReport:
    report_id: str
    title: str
    period_start: str
    period_end: str
    source_ids: tuple
    measures: dict
    created_at: str


def create_report(report_id, title, period_start, period_end, source_ids, measures):
    return AnalysisReport(
        report_id=report_id, title=title, period_start=period_start, period_end=period_end,
        source_ids=tuple(sorted(set(source_ids))), measures=dict(measures),
        created_at=datetime.now(timezone.utc).isoformat(),
    )


DISCLAIMER = (
    "本报告用于讨论资源安排：排序是按既定口径对已有信号的加权汇总，"
    "不构成因果结论，也不代表唯一正确的顺序。"
)

DRIVER_LABELS = {
    "backfill": "覆盖补齐",
    "signal-change": "信号变化",
    "revision": "记录修正",
    "mixed": "混合因素",
    "none": "无变化",
}


def render_dossier(dossiers):
    """候选议题信号一览：每个议题有哪些信号支撑、各自覆盖到哪里。"""
    lines = ["## 候选议题信号一览", ""]
    if not dossiers:
        lines.append("（暂无观察数据）")
        return "\n".join(lines)
    for dossier in dossiers:
        lines.append(f"### {dossier.topic}")
        lines.append("")
        lines.append("| 信号 | 总量 | 记录数 | 来源 | 覆盖地区 | 观测窗口 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for summary in dossier.signals:
            lines.append(
                f"| {summary.signal} | {summary.total:g} | {summary.observations} "
                f"| {', '.join(summary.source_ids)} | {', '.join(summary.regions)} "
                f"| {summary.first_observed} ~ {summary.last_observed} |"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def render_ranking(ranking):
    """单一口径下的排序，含分数构成与待补信息名单。"""
    lines = [f"## 排序（口径：{ranking.weighting.name}）", ""]
    if ranking.ranked:
        lines.append("| 名次 | 议题 | 分数 | 支撑度 | 分数构成（权重×总量） |")
        lines.append("| --- | --- | --- | --- | --- |")
        for entry in ranking.ranked:
            parts = "、".join(
                f"{signal} {value:g}"
                for signal, value in sorted(entry.contributions.items())
            )
            lines.append(
                f"| {entry.rank} | {entry.topic} | {entry.score:.2f} "
                f"| {entry.support:.0%} | {parts} |"
            )
    else:
        lines.append("（当前口径下没有支撑度达标的议题）")
    if ranking.insufficient:
        lines.append("")
        lines.append("### 待补信息（支撑不足，不等于低优先级）")
        lines.append("")
        for entry in ranking.insufficient:
            missing = "、".join(entry.missing_signals) or "—"
            lines.append(f"- {entry.topic}：支撑度 {entry.support:.0%}，缺 {missing}")
    return "\n".join(lines)


def render_comparison(comparison):
    """多套口径下的名次对照，标出对取舍敏感的议题与待补信息。"""
    names = [ranking.weighting.name for ranking in comparison.rankings]
    lines = ["## 不同口径下的名次", ""]
    lines.append("| 议题 | " + " | ".join(names) + " | 名次跨度 |")
    lines.append("| --- | " + " | ".join("---" for _ in names) + " | --- |")
    for movement in comparison.movements:
        cells = [
            str(movement.ranks[name]) if movement.ranks[name] is not None else "待补"
            for name in names
        ]
        spread = "—" if movement.spread is None else str(movement.spread)
        lines.append(f"| {movement.topic} | " + " | ".join(cells) + f" | {spread} |")
    lines.append("")
    lines.append(
        "备注：名次跨度越大，排序对口径取舍越敏感；“待补”表示该口径下支撑度不足，"
        "而非低优先级。"
    )
    if any(ranking.insufficient for ranking in comparison.rankings):
        lines.append("")
        lines.append("### 待补信息（支撑不足，不等于低优先级）")
        lines.append("")
        for ranking in comparison.rankings:
            for entry in ranking.insufficient:
                missing = "、".join(entry.missing_signals) or "—"
                lines.append(
                    f"- {entry.topic}（口径「{ranking.weighting.name}」：缺 {missing}）"
                )
    return "\n".join(lines)


def render_changes(changes):
    """两版数据之间的名次变化归因（讨论线索，非因果证明）。"""
    lines = ["## 数据变化归因（讨论线索，非因果证明）", ""]
    lines.append("| 议题 | 原名次 | 现名次 | 归因 | 新增来源 | 新增地区 | 支撑度 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for change in changes:
        old = str(change.old_rank) if change.old_rank is not None else "待补"
        new = str(change.new_rank) if change.new_rank is not None else "待补"
        lines.append(
            f"| {change.topic} | {old} | {new} "
            f"| {DRIVER_LABELS.get(change.driver, change.driver)} "
            f"| {', '.join(change.sources_added) or '—'} "
            f"| {', '.join(change.regions_added) or '—'} "
            f"| {change.old_support:.0%} → {change.new_support:.0%} |"
        )
    return "\n".join(lines)


def render_decision_report(dossiers, comparison, changes=None):
    """完整的月度决策支持稿：议题档案 + 口径比较（+ 数据变化归因）。"""
    parts = [
        "# 议题候选与排序情景（决策支持稿）",
        "",
        f"> {DISCLAIMER}",
        "",
        render_dossier(dossiers),
        "",
        render_comparison(comparison),
    ]
    if changes is not None:
        parts += ["", render_changes(changes)]
    parts += [
        "",
        "---",
        "口径："
        + "；".join(
            f"「{ranking.weighting.name}」权重 {ranking.weighting.weights}，"
            f"最低支撑度 {ranking.weighting.min_support:.0%}"
            for ranking in comparison.rankings
        ),
    ]
    return "\n".join(parts)
