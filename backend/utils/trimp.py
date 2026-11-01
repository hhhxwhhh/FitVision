"""训练负荷分布引擎（TRIMP / 强度区间分析，纯 Python，无 Django 依赖）。

现有的负荷模型回答的是"我最近累不累"，但它把不同强度的组当成一样重。
实际上，**同样 10 组 60% 1RM 和同样 10 组 90% 1RM 对恢复的影响完全不同**：
高强度组留下的神经肌肉疲劳更久，恢复窗口更长（48–72 小时 vs 24–48 小时）。

本引擎把训练拆到强度区间上，回答三个进阶问题：

1. **我的强度分布合理吗？** —— sRPE-TRIMP 在四个强度区间的占比。
   大量研究表明，**80% 以上的训练量应该落在中低强度区间（< 80% 1RM）**，
   高强度组应该只占 10–20%。绝大多数业余训练者的分布是反的：
   几乎所有组都在 85% 以上，导致慢性疲劳累积、进步停滞。
2. **我的有效训练量够吗？** —— 强度加权组数（intensity-weighted volume）。
   同样 10 组，80% 的强度比 60% 的贡献更多"有效刺激"，但也更难恢复。
3. **我一周该练几次？** —— 基于实际分布给出高强度日的间隔建议。

强度区间的划分参考学术与教练实践中的常见四分法（以 %1RM 计）：

============ ===================== ==========================
区间          名称                   典型用途
============ ===================== ==========================
zone 1        恢复 (< 60%)           热身、循环、恢复训练
zone 2        基础 (60–75%)         容量积累、代谢适应
zone 3        发展 (75–85%)         力量增长、增肌主项
zone 4        强度 (85–100%)        峰值准备、测试
============ ===================== ==========================

**负荷计算方式**：本引擎同时支持两种口径，并给出它们的差异：

- **rpe_trimp**：每组的负荷 = 次数 × RPE（10 分制）。这是 sRPE-TRIMP，
  实践中最可靠（主观用力程度比算出来的 %1RM 更能反映真实强度），
  也是 Mike Tuchscher 体系的核心指标。
- **intensity_trimp**：每组的负荷 = 次数 × %1RM。适合有可靠 e1RM 数据的场景。

两者差距过大时说明数据有问题（重量记错 / 次数填错 / e1RM 估歪），
引擎会把这个信号显式暴露出来，而不是悄悄给一个错的结果。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Sequence

# --------------------------------------------------------------------------- #
# 可调超参
# --------------------------------------------------------------------------- #

#: 强度区间的下界（%1RM）与名称。
ZONE_BOUNDS: tuple[tuple[float, str, str], ...] = (
    (0.0, "zone_1", "恢复"),
    (60.0, "zone_2", "基础"),
    (75.0, "zone_3", "发展"),
    (85.0, "zone_4", "强度"),
)

#: 各强度区间的推荐组数占比（来自"80% 训练量在中低强度"的经验法则）。
#: 顺序对应 ZONE_BOUNDS 的四个区间。
ZONE_SHARE_TARGET: tuple[float, ...] = (0.15, 0.40, 0.30, 0.15)

#: 判定"分布失衡"的容差：实际占比与目标占比的差超过它就给出提醒。
ZONE_SHARE_TOLERANCE = 0.12

#: 高强度组（zone 4）单周建议的最大组数 —— 超过就该往回压。
MAX_HIGH_INTENSITY_SETS_PER_WEEK = 12

#: 两次高强度训练之间的最短间隔（天）。
MIN_HIGH_INTENSITY_GAP_DAYS = 2

#: 单次训练里高强度组数超过该值，就认为这次是"高强度日"。
HIGH_INTENSITY_SESSION_THRESHOLD = 4

#: 计算 %1RM 时的次数上限 —— 超过 12 次的百分比没有意义。
MAX_REPS_FOR_INTENSITY = 12

#: RPE 到强度百分比的近似反查表（RPE 10 分制 → %1RM）。
#: 中间值用线性插值。
RPE_TO_PERCENT: tuple[tuple[float, float], ...] = (
    (10.0, 100.0),
    (9.5, 95.0),
    (9.0, 89.0),
    (8.5, 84.0),
    (8.0, 79.0),
    (7.5, 74.0),
    (7.0, 69.0),
    (6.5, 64.0),
    (6.0, 59.0),
    (5.0, 49.0),
)


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SetLoad:
    """一组的负荷信息。

    `percent` 是该组相对 1RM 的强度（%），`rpe` 是主观用力程度（10 分制）。
    两者至少要有一个才能算负荷 —— 两个都没有时该组被当作"无法计量"跳过。
    """

    reps: int = 0
    weight: float = 0.0
    percent: float | None = None
    rpe: float | None = None
    e1rm: float = 0.0

    @property
    def is_measurable(self) -> bool:
        return self.reps > 0 and (self.percent is not None or self.rpe is not None)


@dataclass(frozen=True)
class ZoneShare:
    """单个强度区间的分布。"""

    key: str
    label: str
    sets: int
    share: float
    target_share: float
    load: float

    @property
    def deviation(self) -> float:
        """实际占比减目标占比 —— 正数表示练多了。"""
        return self.share - self.target_share

    def as_dict(self) -> dict:
        return {
            "key": self.key,
            "label": self.label,
            "sets": self.sets,
            "share": round(self.share, 3),
            "target_share": round(self.target_share, 3),
            "deviation": round(self.deviation, 3),
            "load": round(self.load, 1),
        }


@dataclass(frozen=True)
class SessionLoadProfile:
    """一次训练的强度分布。"""

    date: date | None
    sets: int
    zones: tuple[ZoneShare, ...]
    rpe_trimp: float
    intensity_trimp: float
    high_intensity_sets: int
    balanced: bool
    notes: tuple[str, ...] = ()

    @property
    def zone_map(self) -> dict[str, ZoneShare]:
        return {zone.key: zone for zone in self.zones}

    def as_dict(self) -> dict:
        return {
            "date": self.date.isoformat() if self.date else None,
            "sets": self.sets,
            "zones": [zone.as_dict() for zone in self.zones],
            "rpe_trimp": round(self.rpe_trimp, 1),
            "intensity_trimp": round(self.intensity_trimp, 1),
            "high_intensity_sets": self.high_intensity_sets,
            "balanced": self.balanced,
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class DistributionReport:
    """一段时间的强度分布汇总。"""

    sessions: tuple[SessionLoadProfile, ...]
    weekly: tuple[dict, ...]
    balance_score: float
    verdict: str
    advice: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "sessions": [session.as_dict() for session in self.sessions],
            "weekly": list(self.weekly),
            "balance_score": round(self.balance_score, 3),
            "verdict": self.verdict,
            "advice": list(self.advice),
        }


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def rpe_to_percent(rpe: float) -> float | None:
    """把 RPE（10 分制）近似换算成 %1RM。

    RPE 10 = 极限（100%），RPE 9 ≈ 95%，RPE 8 ≈ 80%（教科书里
    "RPE 8 还能再做 2 次"大致对应 80% 左右的 1RM）。
    """
    if rpe is None:
        return None
    value = float(rpe)
    if value <= 0:
        return None
    value = _clamp(value, 1.0, 10.0)

    table = RPE_TO_PERCENT
    if value >= table[0][0]:
        return table[0][1]
    for (rpe_hi, pct_hi), (rpe_lo, pct_lo) in zip(table, table[1:]):
        if rpe_lo <= value <= rpe_hi:
            if rpe_hi == rpe_lo:
                return pct_hi
            ratio = (value - rpe_lo) / (rpe_hi - rpe_lo)
            return pct_lo + ratio * (pct_hi - pct_lo)
    return table[-1][1]


def percent_from_load(weight: float, reps: int, e1rm: float) -> float | None:
    """由重量、次数和 e1RM 算出该组的强度百分比。

    用 Epley 把这一组折算成它自己的 e1RM（`w × (1 + reps/30)`），
    再除以用户真实的 e1RM。这样"同样 80kg，深蹲 3 次和 12 次不是一回事"
    会被量化出来：次数多 → 折算出的等效 1RM 更高 → 强度百分比更高。
    这与教练"12 次比 3 次更接近力竭"的直觉一致。
    """
    if not e1rm or e1rm <= 0:
        return None
    reps = int(reps or 0)
    if reps <= 0:
        return None
    weight = float(weight or 0.0)
    if weight <= 0:
        # 自重动作没有重量，但它仍然是有效的一组；用次数近似一个低强度。
        return None
    if reps > MAX_REPS_FOR_INTENSITY:
        reps = MAX_REPS_FOR_INTENSITY
    set_e1rm = weight * (1.0 + reps / 30.0)
    percent = set_e1rm / e1rm * 100.0
    return _clamp(percent, 0.0, 100.0)


def zone_for_percent(percent: float) -> tuple[str, str]:
    """返回该强度所属区间的 (key, label)。"""
    value = float(percent or 0.0)
    key, label = ZONE_BOUNDS[0][1], ZONE_BOUNDS[0][2]
    for bound, zone_key, zone_label in ZONE_BOUNDS:
        if value >= bound:
            key, label = zone_key, zone_label
    return key, label


def zone_index(percent: float) -> int:
    """返回该强度在 ZONE_BOUNDS 里的下标。"""
    value = float(percent or 0.0)
    index = 0
    for position, (bound, _, _) in enumerate(ZONE_BOUNDS):
        if value >= bound:
            index = position
    return index


# --------------------------------------------------------------------------- #
# 单次训练
# --------------------------------------------------------------------------- #


def _set_percent(item: SetLoad) -> float | None:
    """确定一组的强度百分比：优先用已有的 percent，其次用 RPE 反查，最后用重量算。"""
    if item.percent is not None:
        return _clamp(float(item.percent), 0.0, 100.0)
    if item.rpe is not None:
        return rpe_to_percent(item.rpe)
    return percent_from_load(item.weight, item.reps, item.e1rm)


def resolve_percent(item: SetLoad) -> float | None:
    """公开的强度百分比解析入口。

    容量引擎（`utils/volume`）需要同一套强度口径，避免两处各算一遍。
    """
    return _set_percent(item)


def resolve_rpe(item: SetLoad, percent: float | None = None) -> float | None:
    """公开的 RPE 解析入口，语义同 `resolve_percent`。"""
    return _set_rpe(item, percent)


def _set_rpe(item: SetLoad, percent: float | None) -> float | None:
    """确定一组的 RPE：有就用，没有就用强度百分比反查。"""
    if item.rpe is not None:
        return _clamp(float(item.rpe), 1.0, 10.0)
    if percent is None:
        return None
    # 强度百分比 → RPE 的近似反查（表格反过来用）。
    table = RPE_TO_PERCENT
    if percent >= table[0][1]:
        return table[0][0]
    for (rpe_hi, pct_hi), (rpe_lo, pct_lo) in zip(table, table[1:]):
        if pct_lo <= percent <= pct_hi:
            if pct_hi == pct_lo:
                return rpe_hi
            ratio = (percent - pct_lo) / (pct_hi - pct_lo)
            return rpe_lo + ratio * (rpe_hi - rpe_lo)
    return table[-1][0]


def session_profile(
    sets: Sequence[SetLoad], day: date | None = None
) -> SessionLoadProfile:
    """算一次训练的强度分布。

    无法计量的组（既没有重量也没有 RPE）会被跳过，并不算进总数 ——
    否则分布会被"不知道强度"的动作稀释，失真。
    """
    counts = [0] * len(ZONE_BOUNDS)
    loads = [0.0] * len(ZONE_BOUNDS)
    rpe_total = 0.0
    intensity_total = 0.0
    measurable = 0
    high_intensity = 0

    for item in sets:
        percent = _set_percent(item)
        if percent is None or not item.is_measurable:
            continue
        measurable += 1
        index = zone_index(percent)
        counts[index] += 1

        rpe = _set_rpe(item, percent)
        rpe_load = item.reps * rpe if rpe is not None else 0.0
        rpe_total += rpe_load

        intensity_load = item.reps * percent
        intensity_total += intensity_load
        loads[index] += rpe_load

        if percent >= ZONE_BOUNDS[-1][0]:
            high_intensity += 1

    notes: list[str] = []
    if measurable == 0:
        notes.append("这一节没有可计量的组（缺少重量或 RPE），无法计算强度分布。")
        return SessionLoadProfile(
            date=day,
            sets=0,
            zones=tuple(
                ZoneShare(key, label, 0, 0.0, target, 0.0)
                for (_, key, label), target in zip(ZONE_BOUNDS, ZONE_SHARE_TARGET)
            ),
            rpe_trimp=0.0,
            intensity_trimp=0.0,
            high_intensity_sets=0,
            balanced=False,
            notes=tuple(notes),
        )

    zones = tuple(
        ZoneShare(
            key=key,
            label=label,
            sets=counts[position],
            share=counts[position] / measurable,
            target_share=ZONE_SHARE_TARGET[position],
            load=loads[position],
        )
        for position, (_, key, label) in enumerate(ZONE_BOUNDS)
    )

    balanced = True
    for zone in zones:
        if abs(zone.deviation) > ZONE_SHARE_TOLERANCE:
            balanced = False
            break

    if not balanced:
        heavy = [z for z in zones if z.deviation > ZONE_SHARE_TOLERANCE]
        if heavy:
            names = "、".join(f"{z.label}（{round(z.share * 100)}%）" for z in heavy)
            notes.append(f"强度分布偏向高强度区间：{names}。")
        else:
            names = "、".join(
                f"{z.label}（{round(z.share * 100)}%）"
                for z in zones
                if z.deviation < -ZONE_SHARE_TOLERANCE
            )
            notes.append(f"高强度训练量偏少：{names} 区间几乎空着。")

    return SessionLoadProfile(
        date=day,
        sets=measurable,
        zones=zones,
        rpe_trimp=rpe_total,
        intensity_trimp=intensity_total,
        high_intensity_sets=high_intensity,
        balanced=balanced,
        notes=tuple(notes),
    )


# --------------------------------------------------------------------------- #
# 多周汇总
# --------------------------------------------------------------------------- #


def weekly_summary(
    sessions: Sequence[SessionLoadProfile], weeks: int = 4
) -> tuple[dict, ...]:
    """按自然周汇总强度分布（最近 `weeks` 周，从早到晚）。"""
    buckets: dict[tuple[int, int], list[SessionLoadProfile]] = {}
    for session in sessions:
        if session.date is None:
            continue
        iso = session.date.isocalendar()
        buckets.setdefault((iso[0], iso[1]), []).append(session)

    ordered = sorted(buckets.items())[-max(1, weeks):]
    summary: list[dict] = []
    for (year, week), items in ordered:
        total_sets = sum(item.sets for item in items)
        counts = [0] * len(ZONE_BOUNDS)
        for item in items:
            for position, zone in enumerate(item.zones):
                counts[position] += zone.sets
        high = sum(item.high_intensity_sets for item in items)
        high_days = sum(1 for item in items if item.high_intensity_sets >= HIGH_INTENSITY_SESSION_THRESHOLD)
        summary.append(
            {
                "year": year,
                "week": week,
                "sessions": len(items),
                "sets": total_sets,
                "zones": [
                    {
                        "key": key,
                        "label": label,
                        "sets": counts[position],
                        "share": round(counts[position] / total_sets, 3) if total_sets else 0.0,
                    }
                    for position, (_, key, label) in enumerate(ZONE_BOUNDS)
                ],
                "rpe_trimp": round(sum(item.rpe_trimp for item in items), 1),
                "intensity_trimp": round(sum(item.intensity_trimp for item in items), 1),
                "high_intensity_sets": high,
                "high_intensity_days": high_days,
                "over_high_intensity_cap": high > MAX_HIGH_INTENSITY_SETS_PER_WEEK,
            }
        )
    return tuple(summary)


def balance_score(sessions: Sequence[SessionLoadProfile]) -> float:
    """给强度分布打一个 0–1 的平衡分。

    用总变差距离（total variation distance）度量"实际分布与目标分布"的差距：
    差距为 0 时得 1 分，完全跑偏时趋近 0 分。
    """
    totals = [0] * len(ZONE_BOUNDS)
    total_sets = 0
    for session in sessions:
        for position, zone in enumerate(session.zones):
            totals[position] += zone.sets
            total_sets += zone.sets
    if total_sets == 0:
        return 0.0
    actual = [value / total_sets for value in totals]
    distance = 0.5 * sum(abs(a - t) for a, t in zip(actual, ZONE_SHARE_TARGET))
    return _clamp(1.0 - distance, 0.0, 1.0)


def high_intensity_gaps(sessions: Sequence[SessionLoadProfile]) -> tuple[int, ...]:
    """返回相邻两个高强度日之间的间隔天数（不足间隔要求的会被标出来）。"""
    days = sorted(
        {
            session.date
            for session in sessions
            if session.date is not None
            and session.high_intensity_sets >= HIGH_INTENSITY_SESSION_THRESHOLD
        }
    )
    gaps: list[int] = []
    for earlier, later in zip(days, days[1:]):
        gaps.append((later - earlier).days)
    return tuple(gaps)


def distribution_report(
    sessions: Sequence[SessionLoadProfile], weeks: int = 4
) -> DistributionReport:
    """汇总一段时间的强度分布，给出平衡分、结论与建议。"""
    ordered = sorted(
        (s for s in sessions if s.date is not None),
        key=lambda s: s.date,
    )
    weekly = weekly_summary(ordered, weeks=weeks)
    score = balance_score(ordered)

    totals = [0] * len(ZONE_BOUNDS)
    total_sets = 0
    high_total = 0
    for session in ordered:
        for position, zone in enumerate(session.zones):
            totals[position] += zone.sets
            total_sets += zone.sets
        high_total += session.high_intensity_sets

    advice: list[str] = []
    if total_sets == 0:
        return DistributionReport(
            sessions=tuple(ordered),
            weekly=weekly,
            balance_score=0.0,
            verdict="数据不足",
            advice=("还没有可计量的训练记录，补上重量或 RPE 后就能看到强度分布。",),
        )

    shares = [value / total_sets for value in totals]
    heavy_zones = [
        (ZONE_BOUNDS[position][1], ZONE_BOUNDS[position][2], shares[position])
        for position in range(len(ZONE_BOUNDS))
        if shares[position] > ZONE_SHARE_TARGET[position] + ZONE_SHARE_TOLERANCE
    ]
    light_zones = [
        (ZONE_BOUNDS[position][1], ZONE_BOUNDS[position][2], shares[position])
        for position in range(len(ZONE_BOUNDS))
        if shares[position] < ZONE_SHARE_TARGET[position] - ZONE_SHARE_TOLERANCE
    ]

    if heavy_zones:
        names = "、".join(f"{label}（{round(share * 100)}%）" for _, label, share in heavy_zones)
        advice.append(
            f"高强度占比偏高：{names}。把其中一部分降到 70–80% 1RM，"
            "恢复会快很多，进步反而更稳。"
        )
    if light_zones:
        names = "、".join(f"{label}（{round(share * 100)}%）" for _, label, share in light_zones)
        advice.append(
            f"{names} 区间练得太少。补一些 60–75% 1RM 的容量组，"
            "基础打牢了高强度才推得动。"
        )

    if high_total > MAX_HIGH_INTENSITY_SETS_PER_WEEK * max(1, len(weekly)):
        advice.append(
            f"高强度组累计 {high_total} 组，超过单周 {MAX_HIGH_INTENSITY_SETS_PER_WEEK} 组的上限，"
            "考虑插入一个减量周。"
        )

    gaps = high_intensity_gaps(ordered)
    too_close = [gap for gap in gaps if gap < MIN_HIGH_INTENSITY_GAP_DAYS]
    if too_close:
        advice.append(
            f"有 {len(too_close)} 次高强度训练间隔不足 {MIN_HIGH_INTENSITY_GAP_DAYS} 天，"
            "神经系统还没恢复就又上强度，容易累积疲劳。"
        )

    if score >= 0.9:
        verdict = "分布良好"
    elif score >= 0.75:
        verdict = "基本合理"
    elif score >= 0.6:
        verdict = "轻度失衡"
    else:
        verdict = "明显失衡"

    return DistributionReport(
        sessions=tuple(ordered),
        weekly=weekly,
        balance_score=score,
        verdict=verdict,
        advice=tuple(advice),
    )
