"""命令行入口：查看议题档案、比较口径、留档与核验月度决定。"""

import argparse

from .decisions import DecisionLedger
from .dossier import build_dossiers
from .explain import explain_changes
from .ranking import Weighting, compare_weightings
from .report import (
    render_changes,
    render_decision_report,
    render_dossier,
    render_ranking,
)
from .store import load_observations


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (ValueError, KeyError, FileExistsError) as exc:
        parser.exit(2, f"错误：{exc}\n")


def _build_parser():
    parser = argparse.ArgumentParser(
        prog="signal_lab",
        description="议题优先级分析：决策支持工具，输出不构成因果结论或唯一正确顺序。",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("dossier", help="查看每个候选议题的信号支撑与覆盖范围")
    p.add_argument("data", help="观察数据 JSON")
    p.add_argument("--period", help="只统计该月份，如 2026-11")
    p.set_defaults(func=_cmd_dossier)

    p = sub.add_parser("compare", help="比较不同口径（权重取舍）下的排序")
    p.add_argument("data", help="观察数据 JSON")
    p.add_argument("--weights", action="append", required=True,
                   metavar="名称:信号=权重,...", help="一套口径；可重复提供以比较")
    p.add_argument("--min-support", type=float, default=0.5,
                   help="纳入排序所需的最低支撑度（默认 0.5）")
    p.add_argument("--candidates", help="逗号分隔的候选议题（可含暂无数据的议题）")
    p.add_argument("--period", help="只统计该月份，如 2026-11")
    p.set_defaults(func=_cmd_compare)

    p = sub.add_parser("explain", help="对比两版数据，解释名次变化来自哪里")
    p.add_argument("old_data", help="旧版观察数据 JSON")
    p.add_argument("new_data", help="新版观察数据 JSON")
    p.add_argument("--weights", required=True, metavar="信号=权重,...",
                   help="单一口径；两版数据用同一口径排序")
    p.add_argument("--min-support", type=float, default=0.5)
    p.set_defaults(func=_cmd_explain)

    p = sub.add_parser("decide", help="留档月度决定（数据快照 + 口径 + 理由，只增不改）")
    p.add_argument("data", help="作出决定时使用的观察数据 JSON")
    p.add_argument("--ledger", required=True, help="决定档案目录")
    p.add_argument("--decision-id", required=True, help="决定标识，如 2026-11")
    p.add_argument("--period", required=True, help="决定所属月份，如 2026-11")
    p.add_argument("--select", required=True, help="逗号分隔的选定议题")
    p.add_argument("--rationale", required=True, help="选择理由")
    p.add_argument("--weights", required=True, metavar="信号=权重,...")
    p.add_argument("--min-support", type=float, default=0.5)
    p.add_argument("--candidates", help="逗号分隔的候选议题（可含暂无数据的议题）")
    p.set_defaults(func=_cmd_decide)

    p = sub.add_parser("pending", help="用最近留档口径重算待决策名单（不改写留档）")
    p.add_argument("data", help="当前观察数据 JSON")
    p.add_argument("--ledger", required=True, help="决定档案目录")
    p.add_argument("--candidates", help="逗号分隔的候选议题")
    p.set_defaults(func=_cmd_pending)

    p = sub.add_parser("verify", help="核验留档决定的数据与口径未被改动")
    p.add_argument("--ledger", required=True, help="决定档案目录")
    p.add_argument("--decision-id", help="只核验指定决定；缺省核验全部")
    p.set_defaults(func=_cmd_verify)

    return parser


def _cmd_dossier(args):
    observations = _filter_period(load_observations(args.data), args.period)
    print(render_dossier(build_dossiers(observations)))
    return 0


def _cmd_compare(args):
    observations = _filter_period(load_observations(args.data), args.period)
    weightings = [
        _parse_weighting(spec, args.min_support, f"口径{index}")
        for index, spec in enumerate(args.weights, start=1)
    ]
    dossiers = build_dossiers(observations)
    comparison = compare_weightings(dossiers, weightings, _split(args.candidates))
    print(render_decision_report(dossiers, comparison))
    return 0


def _cmd_explain(args):
    weighting = _parse_weighting(args.weights, args.min_support)
    changes = explain_changes(
        load_observations(args.old_data), load_observations(args.new_data), weighting
    )
    print(render_changes(changes))
    return 0


def _cmd_decide(args):
    weighting = _parse_weighting(args.weights, args.min_support)
    ledger = DecisionLedger(args.ledger)
    record = ledger.record(
        decision_id=args.decision_id,
        period=args.period,
        weighting=weighting,
        observations=load_observations(args.data),
        selected=_split(args.select),
        rationale=args.rationale,
        candidates=_split(args.candidates),
    )
    print(
        f"已留档决定 {record.decision_id}（{record.period}）："
        f"{len(record.observations)} 条观察，快照 {record.snapshot[:12]}…"
    )
    print(f"档案文件：{ledger.path_for(record.decision_id)}")
    print("选定议题：" + "、".join(record.selected))
    if record.insufficient:
        print("待补信息：" + "、".join(record.insufficient))
    return 0


def _cmd_pending(args):
    ledger = DecisionLedger(args.ledger)
    ranking = ledger.recompute_pending(
        load_observations(args.data), candidates=_split(args.candidates)
    )
    print(render_ranking(ranking))
    return 0


def _cmd_verify(args):
    ledger = DecisionLedger(args.ledger)
    results = (
        (ledger.verify(args.decision_id),) if args.decision_id else ledger.verify_all()
    )
    if not results:
        print("档案库为空。")
        return 0
    ok = True
    for result in results:
        if result.ok:
            print(f"✓ {result.decision_id}：留档完整，数据与口径一致")
        else:
            ok = False
            print(f"✗ {result.decision_id}：留档核验未通过")
            for problem in result.problems:
                print(f"  - {problem}")
    return 0 if ok else 1


def _parse_weighting(spec, min_support, default_name="自定义口径"):
    """解析「名称:信号=权重,...」；无名时使用缺省名称。"""
    name, sep, rest = spec.partition(":")
    if not sep:
        name, rest = default_name, spec
    weights = {}
    for part in rest.split(","):
        key, eq, value = part.partition("=")
        if not eq:
            raise ValueError(f"权重格式应为 信号=数值：{part!r}")
        weights[key.strip()] = float(value)
    return Weighting(name=name.strip() or default_name, weights=weights,
                     min_support=min_support)


def _split(text):
    if not text:
        return ()
    return tuple(part.strip() for part in text.split(",") if part.strip())


def _filter_period(observations, period):
    if not period:
        return observations
    year, month = (int(part) for part in period.split("-"))
    return [
        obs for obs in observations
        if (obs.observed_on.year, obs.observed_on.month) == (year, month)
    ]


if __name__ == "__main__":
    raise SystemExit(main())
