"""力量评估与渐进超负荷引擎（纯 Python，无 Django 依赖）。

回答三个训练中最实际的问题：

1. **我到底能推多重？** —— 估计等效 1RM（e1RM）。
2. **下一组该上多少重量、几次？** —— 渐进超负荷处方。
3. **该减量了吗？** —— 依据 e1RM 趋势与整体疲劳给出减量建议。

e1RM 有三条互相独立的来源，按可靠性排序：

- **次数公式**（Epley / Brzycki / Lombardi / Wathan 2018）：最常用，但次数越多误差越大，
  因此取四个公式里**最保守**的那个，避免高估自己。
- **速度推次**（VBT）：杠铃动作的向心平均速度与"这一重量还能做几次"高度相关，
  用速度反推次数上限再折算 e1RM。速度来源是刚体杠铃轨迹，基本不受主观疲劳影响。
- **RPE / RIR 反推**：知道"还能再做几次"（RIR）时，可以直接用百分比表反推 1RM。

三条来源可以互相校验：差异过大时说明数据有问题（配重记错 / 次数填错）。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Iterable, Sequence

# --------------------------------------------------------------------------- #
# 可调超参
# --------------------------------------------------------------------------- #

#: 超过该次数不再估计 1RM —— 12 次以上的公式误差已经大于训练价值。
MAX_REPS_FOR_ESTIMATE = 12

#: 杠铃向心速度达到该值（m/s）时，基本只剩 1 次余量。
VELOCITY_AT_ONE_REP = 0.30
#: 每提升 0.1 m/s，可以多做的次数（经验值，约 20 reps/(m/s)）。
VELOCITY_REPS_PER_MS = 20.0
#: 速度推次得到的次数上限。
MAX_VELOCITY_REPS = 15

#: 默认配重片间隔（kg）。
PLATE_INCREMENT = 2.5

#: 减量周：重量下调比例。
DELOAD_FACTOR = 0.9
#: 连续多少次训练 e1RM 没有提升就建议减量。
STALL_SESSIONS_FOR_DELOAD = 3
#: e1RM 下降超过该比例即视为退步。
DECLINE_THRESHOLD = 0.03


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SetResult:
    """一组训练结果。

    `rir` = 还能再做几次（reps in reserve），`rpe` = 主观用力程度（1-10），
    `mean_velocity` = 向心平均速度（m/s）。三者都是可选的，引擎会在有哪个就用哪个。
    """

    weight: float = 0.0
    reps: int = 0
    rir: int | None = None
    rpe: float | None = None
    mean_velocity: float | None = None


@dataclass(frozen=True)
class StrengthEstimate:
    """一次 e1RM 估计及其来源。"""

    e1rm: float
    method: str  # rep_formula | velocity | rir
    confidence: float  # 0-1
    details: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "e1rm": round(self.e1rm, 1),
            "method": self.method,
            "confidence": round(self.confidence, 2),
            **{key: value for key, value in self.details.items()},
        }


@dataclass(frozen=True)
class Prescription:
    """下一组 / 下一次训练的建议。"""

    weight: float
    target_reps: int
    target_rir: int
    changed: bool
    reason: str

    def as_dict(self) -> dict:
        return {
            "weight": round(self.weight, 1),
            "target_reps": self.target_reps,
            "target_rir": self.target_rir,
            "changed": self.changed,
            "reason": self.reason,
        }


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _valid_weight(weight: float) -> float:
    return max(0.0, float(weight or 0.0))


def _valid_reps(reps: int) -> int:
    return max(0, int(reps or 0))


# --------------------------------------------------------------------------- #
# 1RM 公式
# --------------------------------------------------------------------------- #


def epley_1rm(weight: float, reps: int) -> float:
    """Epley：`w × (1 + reps / 30)`。经典公式，次数少时最准。"""
    weight, reps = _valid_weight(weight), _valid_reps(reps)
    if reps <= 0:
        return 0.0
    if reps == 1:
        return weight
    return weight * (1.0 + reps / 30.0)


def brzycki_1rm(weight: float, reps: int) -> float:
    """Brzycki：`w × 36 / (37 - reps)`。次数越多越保守。"""
    weight, reps = _valid_weight(weight), _valid_reps(reps)
    if reps <= 0:
        return 0.0
    if reps >= 37:
        return 0.0
    return weight * 36.0 / (37.0 - reps)


def lombardi_1rm(weight: float, reps: int) -> float:
    """Lombardi：`w × reps^0.10`。"""
    weight, reps = _valid_weight(weight), _valid_reps(reps)
    if reps <= 0:
        return 0.0
    return weight * (reps ** 0.10)


def wathan_1rm(weight: float, reps: int) -> float:
    """Wathan (2018)：`100w / (48.8 + 53.8·e^(-0.075·reps))`。

    目前被认为在 1–12 次区间里误差最小的经验公式之一。
    """
    weight, reps = _valid_weight(weight), _valid_reps(reps)
    if reps <= 0:
        return 0.0
    denominator = 48.8 + 53.8 * math.exp(-0.075 * reps)
    return 100.0 * weight / denominator


def rep_formula_estimates(weight: float, reps: int) -> dict[str, float]:
    """给出全部次数公式的估计值。"""
    weight, reps = _valid_weight(weight), _valid_reps(reps)
    if reps <= 0 or weight <= 0:
        return {}
    estimates = {
        "epley": epley_1rm(weight, reps),
        "brzycki": brzycki_1rm(weight, reps),
        "lombardi": lombardi_1rm(weight, reps),
        "wathan": wathan_1rm(weight, reps),
    }
    return {key: value for key, value in estimates.items() if value > 0}


def estimate_1rm(weight: float, reps: int) -> StrengthEstimate | None:
    """用次数公式保守估计 e1RM。

    取四个公式中的**最小值**：宁可低估也不要高估，否则会给出过重的处方。
    次数为 0、重量为 0 或超过 `MAX_REPS_FOR_ESTIMATE` 时不返回结果。
    """
    weight, reps = _valid_weight(weight), _valid_reps(reps)
    if weight <= 0 or reps <= 0:
        return None
    if reps > MAX_REPS_FOR_ESTIMATE:
        return None

    estimates = rep_formula_estimates(weight, reps)
    if not estimates:
        return None

    value = min(estimates.values())
    # 次数越多，公式越不可靠；置信度从 1.0 线性衰减到 0.4。
    confidence = 1.0 - 0.6 * ((reps - 1) / float(MAX_REPS_FOR_ESTIMATE - 1))
    return StrengthEstimate(
        e1rm=value,
        method="rep_formula",
        confidence=_clamp(confidence, 0.4, 1.0),
        details={
            "weight": weight,
            "reps": reps,
            "estimates": {key: round(item, 1) for key, item in estimates.items()},
        },
    )


# --------------------------------------------------------------------------- #
# 速度推次（VBT）
# --------------------------------------------------------------------------- #


def velocity_rep_capacity(mean_velocity: float) -> float:
    """由向心平均速度推出"这个重量最多还能做几次"。

    线性标定：`0.30 m/s` ≈ 1 次余量，每提高 0.1 m/s 多约 2 次。
    """
    if mean_velocity is None:
        return 0.0
    velocity = float(mean_velocity)
    if velocity <= 0:
        return 0.0
    capacity = 1.0 + (velocity - VELOCITY_AT_ONE_REP) * VELOCITY_REPS_PER_MS
    return _clamp(capacity, 0.0, float(MAX_VELOCITY_REPS))


def estimate_1rm_from_velocity(weight: float, mean_velocity: float) -> StrengthEstimate | None:
    """用速度反推次数上限，再折算 e1RM。"""
    weight = _valid_weight(weight)
    capacity = velocity_rep_capacity(mean_velocity)
    if weight <= 0 or capacity <= 0:
        return None
    e1rm = weight * (1.0 + capacity / 30.0)
    # 速度越接近 1RM，估算越可靠。
    confidence = _clamp(1.0 - (capacity - 1.0) / 12.0, 0.4, 0.95)
    return StrengthEstimate(
        e1rm=e1rm,
        method="velocity",
        confidence=confidence,
        details={
            "weight": weight,
            "mean_velocity": round(float(mean_velocity), 3),
            "rep_capacity": round(capacity, 1),
        },
    )


# --------------------------------------------------------------------------- #
# RPE / RIR
# --------------------------------------------------------------------------- #


def rir_from_rpe(rpe: float) -> float:
    """RPE（1-10）→ 还能再做几次（RIR）。10 = 0 次，8 = 2 次。"""
    if rpe is None:
        return 0.0
    value = float(rpe)
    if value <= 0:
        return 0.0
    return _clamp(10.0 - value, 0.0, 5.0)


def rep_percentage(reps: int, rir: int = 0) -> float:
    """完成 `reps` 次且保留 `rir` 次余量时，应该用 1RM 的百分之多少。

    与常见的"次数百分比表"一致：5 次 @RIR0 ≈ 88%、5 次 @RIR2 ≈ 83%、10 次 @RIR2 ≈ 73%。
    """
    reps, rir = _valid_reps(reps), max(0, int(rir or 0))
    if reps <= 0:
        return 1.0
    rep_max = reps + rir
    if rep_max <= 1:
        return 1.0
    return 1.0 / (1.0 + (rep_max - 1) / 30.0)


def estimate_1rm_from_rir(weight: float, reps: int, rir: int) -> StrengthEstimate | None:
    """用 RIR 反推 e1RM。"""
    weight = _valid_weight(weight)
    if weight <= 0 or _valid_reps(reps) <= 0:
        return None
    rir = max(0, int(rir or 0))
    percentage = rep_percentage(reps, rir)
    if percentage <= 0:
        return None
    return StrengthEstimate(
        e1rm=weight / percentage,
        method="rir",
        confidence=0.75,
        details={"weight": weight, "reps": _valid_reps(reps), "rir": rir},
    )


# --------------------------------------------------------------------------- #
# 汇总估计
# --------------------------------------------------------------------------- #


def best_set_estimate(sets: Sequence[SetResult]) -> StrengthEstimate | None:
    """从一组训练结果里挑出最可信的 e1RM 估计。

    优先级：速度 > RIR > 次数公式；同一方法里取置信度最高的（即信息最全的）。
    """
    if not sets:
        return None

    candidates: list[StrengthEstimate] = []
    for item in sets:
        reps = _valid_reps(item.reps)
        weight = _valid_weight(item.weight)
        if item.mean_velocity is not None:
            estimate = estimate_1rm_from_velocity(weight, item.mean_velocity)
            if estimate:
                candidates.append(estimate)
        if item.rir is not None and reps > 0:
            estimate = estimate_1rm_from_rir(weight, reps, item.rir)
            if estimate:
                candidates.append(estimate)
        estimate = estimate_1rm(weight, reps)
        if estimate:
            candidates.append(estimate)

    if not candidates:
        return None

    priority = {"velocity": 3, "rir": 2, "rep_formula": 1}
    candidates.sort(key=lambda item: (priority.get(item.method, 0), item.confidence), reverse=True)
    return candidates[0]


def estimate_session_e1rm(sets: Sequence[SetResult]) -> StrengthEstimate | None:
    """一次训练里取**最重那一组**的 e1RM 作为该动作的当前水平。

    最重的一组通常也最接近力竭，是对 1RM 最贴近的估计。
    """
    usable = [item for item in sets if _valid_weight(item.weight) > 0 and _valid_reps(item.reps) > 0]
    if not usable:
        return best_set_estimate(sets)
    heaviest = max(usable, key=lambda item: _valid_weight(item.weight))
    return best_set_estimate([heaviest])


def compare_estimates(estimates: Sequence[StrengthEstimate]) -> dict:
    """比较多条来源的估计，返回一致性与差异。

    差异过大通常意味着数据录入有误（重量或次数填错），值得在 UI 上提示。
    """
    values = [item.e1rm for item in estimates if item.e1rm > 0]
    if len(values) < 2:
        return {"count": len(values), "spread": 0.0, "consistent": True, "mean": values[0] if values else 0.0}

    mean = sum(values) / len(values)
    spread = (max(values) - min(values)) / mean if mean > 0 else 0.0
    return {
        "count": len(values),
        "spread": round(spread, 4),
        "consistent": spread <= 0.12,
        "mean": round(mean, 1),
    }


# --------------------------------------------------------------------------- #
# 渐进超负荷处方
# --------------------------------------------------------------------------- #


def round_to_increment(value: float, increment: float = PLATE_INCREMENT) -> float:
    """向下取整到配重片间隔（宁可轻一点，不要凑不上的重量）。"""
    if increment <= 0:
        return round(value, 2)
    if value <= 0:
        return 0.0
    return round(math.floor(value / increment + 1e-9) * increment, 2)


def prescribe_load(
    e1rm: float,
    target_reps: int,
    target_rir: int = 2,
    increment: float = PLATE_INCREMENT,
) -> float:
    """由 e1RM 推导下一次训练该用多少重量。"""
    if e1rm <= 0:
        return 0.0
    percentage = rep_percentage(target_reps, target_rir)
    return round_to_increment(e1rm * percentage, increment)


def next_prescription(
    e1rm: float,
    last_weight: float,
    last_reps: int,
    target_reps: int,
    target_rir: int = 2,
    increment: float = PLATE_INCREMENT,
) -> Prescription:
    """双进阶（double progression）处方。

    - 上次做满了目标次数 → 加重 2.5%（并至少加一个配重片间隔）。
    - 没做满 → 保持重量，次数往上加。
    """
    if e1rm <= 0:
        return Prescription(0.0, target_reps, target_rir, False, "还没有足够数据，先记录几组")

    weight = _valid_weight(last_weight) or prescribe_load(e1rm, target_reps, target_rir, increment)
    done = _valid_reps(last_reps)

    if done >= target_reps:
        bump = max(increment, round(weight * 0.025 / increment) * increment)
        new_weight = round_to_increment(weight + bump, increment)
        return Prescription(
            new_weight,
            target_reps,
            target_rir,
            True,
            f"上次做满 {done} 次，加重到 {new_weight:g} kg",
        )

    return Prescription(
        round_to_increment(weight, increment),
        target_reps,
        target_rir,
        False,
        f"继续 {weight:g} kg，本组目标 {target_reps} 次（上次 {done} 次）",
    )


# --------------------------------------------------------------------------- #
# 趋势与减量
# --------------------------------------------------------------------------- #


def e1rm_trend(values: Sequence[float]) -> float:
    """e1RM 序列的最小二乘斜率（kg/次）。"""
    clean = [float(value) for value in values if value and value > 0]
    if len(clean) < 2:
        return 0.0
    n = len(clean)
    mean_x = (n - 1) / 2.0
    mean_y = sum(clean) / n
    numerator = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(clean))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def deload_advice(
    e1rms: Sequence[float],
    fatigue: float = 0.0,
    sessions_without_progress: int | None = None,
) -> dict:
    """判断是否该安排一个减量周。

    三个触发条件（满足任意一条即建议减量）：
    1. e1RM 相比峰值下降超过 3%；
    2. 连续 N 次训练 e1RM 没有提升；
    3. 整体疲劳度已经很高（≥ 0.7）。
    """
    clean = [float(value) for value in e1rms if value and value > 0]
    reasons: list[str] = []

    if len(clean) >= 2:
        peak = max(clean)
        latest = clean[-1]
        if peak > 0 and (peak - latest) / peak >= DECLINE_THRESHOLD:
            reasons.append(f"e1RM 相比峰值下降了 {(peak - latest) / peak * 100:.1f}%")

    if sessions_without_progress is None:
        sessions_without_progress = _stall_sessions(clean)
    if sessions_without_progress >= STALL_SESSIONS_FOR_DELOAD:
        reasons.append(f"连续 {sessions_without_progress} 次训练 e1RM 没有提升")

    if fatigue >= 0.7:
        reasons.append(f"整体疲劳度偏高（{fatigue:.0%}）")

    if not reasons:
        return {"deload": False, "factor": 1.0, "reasons": [], "advice": ""}

    return {
        "deload": True,
        "factor": DELOAD_FACTOR,
        "reasons": reasons,
        "advice": "下一周把重量降到 90%，次数保持不变，让神经与结缔组织跟上。",
    }


def _stall_sessions(values: Sequence[float]) -> int:
    """从最后一次提升算起，已经连续多少次没有超过它。"""
    if len(values) < 2:
        return 0
    best = values[0]
    stall = 0
    for value in values[1:]:
        if value > best + 1e-6:
            best = value
            stall = 0
        else:
            stall += 1
    return stall


def strength_summary(
    e1rms: Sequence[float],
    sessions: Sequence[date] | None = None,
    fatigue: float = 0.0,
) -> dict:
    """给 UI 用的力量摘要。"""
    clean = [float(value) for value in e1rms if value and value > 0]
    if not clean:
        return {
            "latest": 0.0,
            "best": 0.0,
            "trend": 0.0,
            "trend_percent": 0.0,
            "sessions": 0,
            "deload": deload_advice([], fatigue=fatigue),
        }

    latest = clean[-1]
    best = max(clean)
    trend = e1rm_trend(clean)
    first = clean[0]
    trend_percent = ((latest - first) / first * 100.0) if first > 0 else 0.0

    first_session = None
    if sessions:
        raw = sessions[0]
        first_session = raw.isoformat() if hasattr(raw, "isoformat") else str(raw)

    return {
        "latest": round(latest, 1),
        "best": round(best, 1),
        "trend": round(trend, 3),
        "trend_percent": round(trend_percent, 2),
        "sessions": len(clean),
        "first_session": first_session,
        "deload": deload_advice(clean, fatigue=fatigue),
    }


def build_sets(
    weights: Sequence | None,
    reps: Sequence | None,
    rir: int | None = None,
) -> list[SetResult]:
    """把数据库里的两个 JSON 列表拼成一组组训练结果。

    `weights_used` 与 `reps_completed` 逐位对应；长度不一致时以较短的为准，
    缺重量的一组按自重（0）处理，不参与重量类估计。
    `rir`（还能再做几次）作用在**最重的那一组**上 —— 用户填的 RIR 通常描述的
    就是 hardest set，这样 RIR 反推 1RM 时不会张冠李戴。
    """
    weight_list = list(weights or [])
    rep_list = list(reps or [])
    sets: list[SetResult] = []
    for index in range(min(len(weight_list), len(rep_list))):
        try:
            weight = float(weight_list[index])
        except (TypeError, ValueError):
            weight = 0.0
        try:
            count = int(rep_list[index])
        except (TypeError, ValueError):
            count = 0
        sets.append(SetResult(weight=weight, reps=max(0, count)))

    if rir is not None and sets:
        heaviest = max(range(len(sets)), key=lambda i: sets[i].weight)
        current = sets[heaviest]
        sets[heaviest] = SetResult(
            weight=current.weight,
            reps=current.reps,
            rir=max(0, int(rir)),
            rpe=current.rpe,
            mean_velocity=current.mean_velocity,
        )
    return sets


def best_e1rm(estimates: Iterable[StrengthEstimate | None]) -> float:
    """从多次估计里取最大值（历史最好 e1RM）。"""
    values = [item.e1rm for item in estimates if item and item.e1rm > 0]
    return max(values) if values else 0.0
