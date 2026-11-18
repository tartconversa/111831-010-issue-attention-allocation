from collections import defaultdict


def compare_periods(observations, start, end, *, region=None):
    """汇总两个周期内的观察值与来源覆盖数量。"""
    periods = ((start[0], start[1]), (end[0], end[1]))
    totals = [defaultdict(float), defaultdict(float)]
    sources = [defaultdict(set), defaultdict(set)]
    for observation in observations:
        if region is not None and observation.region != region:
            continue
        key = (observation.observed_on.year, observation.observed_on.month)
        if key not in periods:
            continue
        slot = periods.index(key)
        totals[slot][observation.topic] += observation.value
        sources[slot][observation.topic].add(observation.source_id)
    topics = sorted(set(totals[0]) | set(totals[1]))
    return {topic: {
        "start_value": totals[0][topic], "end_value": totals[1][topic],
        "start_sources": len(sources[0][topic]), "end_sources": len(sources[1][topic]),
    } for topic in topics}
