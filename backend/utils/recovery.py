"""分肌群恢复模型（纯 Python，无 Django 依赖）。

`utils/readiness.py` 回答的是"整体上我今天能不能练"，这一层回答的是
**"今天该练哪个部位"**。两者互补：整体负荷模型看的是心血管/神经系统的
总压力，而肌群恢复看的是局部肌肉损伤的消退。

模型思路：

1. **刺激量（stimulus）**
   每个动作记录折算成"有效容量"：抗阻动作按 `组数 × 次数 / 10`（3×10 记作 3 个
   单位），计时动作（平板支撑、靠墙静蹲）按 `秒 / 60`。动作质量只做轻微调制，
   因为动作变形既不减少机械张力，也不减少代谢压力。

2. **协同肌扩散（synergy）**
   练胸会顺带疲劳肩和三头，练背会顺带疲劳二头。用一个固定的协同权重矩阵
   把主目标肌群的刺激量按比例摊到协同肌上（对角线为 1.0）。

3. **指数衰减恢复**
   残余疲劳 `R = Σ s_i · 0.5^(Δt / H)`，`H` 是该肌群的恢复半衰期（小时）。
   大肌群（腿、臀、背）半衰期长，小肌群（腹、手臂）短。
   用半衰期而不是线性衰减，是因为 DOMS 与实际力量恢复都近似一阶动力学。

4. **超量恢复加成**
   恢复度接近 100% 且本周容量还在最优区间内时，给出 >1 的推荐加权
   （"正好该练它了"）；反过来，残余疲劳高的肌群会被显著降权。

所有阈值集中在文件头部，便于调参与写进文档。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Iterable, Mapping, Sequence

# --------------------------------------------------------------------------- #
# 可调超参
# --------------------------------------------------------------------------- #

#: 主目标肌群 → 恢复半衰期（小时）。大肌群 / 离心成分多的动作恢复更慢。
MUSCLE_HALFLIFE_HOURS: dict[str, float] = {
    "legs": 72.0,
    "glutes": 66.0,
    "back": 60.0,
    "full_body": 54.0,
    "chest": 48.0,
    "shoulders": 42.0,
    "arms": 30.0,
    "abs": 24.0,
}

#: 未登记肌群（例如历史脏数据）使用的默认半衰期。
DEFAULT_HALFLIFE_HOURS = 48.0

#: 主目标肌群 → 协同肌权重。对角线隐含为 1.0，不需要写出。
MUSCLE_SYNERGY: dict[str, dict[str, float]] = {
    "chest": {"shoulders": 0.45, "arms": 0.35},
    "back": {"arms": 0.45, "shoulders": 0.20, "abs": 0.10},
    "shoulders": {"arms": 0.40, "back": 0.20},
    "arms": {"shoulders": 0.15},
    "legs": {"glutes": 0.50, "abs": 0.10},
    "glutes": {"legs": 0.35, "abs": 0.10},
    "abs": {},
    "full_body": {
        "chest": 0.30,
        "back": 0.30,
        "legs": 0.30,
        "shoulders": 0.25,
        "glutes": 0.25,
        "arms": 0.20,
        "abs": 0.20,
    },
}

#: 单个肌群"完全力竭一次"对应的残余疲劳参考值，用来把残余疲劳归一化成 0-100。
#: 大约等于 3 个动作的 3×10 容量带协同扩散后的量级。
MUSCLE_CAPACITY: dict[str, float] = {
    "legs": 9.0,
    "glutes": 7.0,
    "back": 7.0,
    "chest": 6.0,
    "shoulders": 5.0,
    "arms": 4.0,
    "abs": 3.5,
    "full_body": 6.0,
}
DEFAULT_CAPACITY = 6.0

#: 恢复度 ≥ 该值即视为"可以再练"（对应残余疲劳 ≤ 容量的 15%）。
READY_THRESHOLD = 85.0
#: 恢复度低于该值即视为"仍在酸痛窗口"，应当降权。
FATIGUED_THRESHOLD = 60.0

#: 证据支持的每周每肌群有效组数区间（10–20 组），用来给容量建议。
WEEKLY_SETS_MIN = 10.0
WEEKLY_SETS_MAX = 20.0

#: 推荐加权区间：完全疲劳 → 0.55，完全恢复 → 1.15。
MULTIPLIER_MIN = 0.55
MULTIPLIER_SPAN = 0.60

MUSCLE_LABELS: dict[str, str] = {
    "chest": "胸部",
    "back": "背部",
    "shoulders": "肩部",
    "arms": "手臂",
    "abs": "腹部",
    "legs": "腿部",
    "glutes": "臀部",
    "full_body": "全身",
}

MUSCLE_ORDER: tuple[str, ...] = (
    "chest",
    "back",
    "shoulders",
    "arms",
    "abs",
    "legs",
    "glutes",
)


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MuscleWork:
    """一次动作记录对某个肌群的刺激。

    `sets` / `reps` 用于抗阻动作，`seconds` 用于计时动作，两者可以并存
    （例如"3 组 × 40 秒平板支撑"）。
    """

    muscle: str
    at: datetime
    sets: int = 0
    reps: int = 0
    seconds: float = 0.0
    form_score: float | None = None


@dataclass(frozen=True)
class MuscleState:
    """单个肌群的恢复快照。"""

    muscle: str
    label: str
    residual: float
    recovery: float
    status: str  # ready | caution | fatigued
    hours_to_ready: float
    weekly_sets: float
    volume_status: str  # under | optimal | over | idle
    multiplier: float

    def as_dict(self) -> dict:
        return {
            "muscle": self.muscle,
            "label": self.label,
            "residual": round(self.residual, 2),
            "recovery": round(self.recovery, 1),
            "status": self.status,
            "hours_to_ready": round(self.hours_to_ready, 1),
            "weekly_sets": round(self.weekly_sets, 1),
            "volume_status": self.volume_status,
            "multiplier": round(self.multiplier, 3),
        }


@dataclass(frozen=True)
class RecoverySnapshot:
    """全部肌群的恢复快照 + 今日建议。"""

    muscles: dict[str, MuscleState] = field(default_factory=dict)
    focus: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "muscles": [state.as_dict() for state in self.ordered()],
            "focus": list(self.focus),
            "avoid": list(self.avoid),
        }

    def ordered(self) -> list[MuscleState]:
        """按 UI 固定顺序输出，缺失的肌群补一个"完全恢复"的空态。"""
        keys = list(MUSCLE_ORDER) + [key for key in self.muscles if key not in MUSCLE_ORDER]
        result: list[MuscleState] = []
        for key in keys:
            state = self.muscles.get(key)
            if state is None:
                state = MuscleState(
                    muscle=key,
                    label=MUSCLE_LABELS.get(key, key),
                    residual=0.0,
                    recovery=100.0,
                    status="ready",
                    hours_to_ready=0.0,
                    weekly_sets=0.0,
                    volume_status="idle",
                    multiplier=MULTIPLIER_MIN + MULTIPLIER_SPAN,
                )
            result.append(state)
        return result

    def multiplier_for(self, muscle: str) -> float:
        """推荐排序用的加权系数：越疲劳越低。"""
        state = self.muscles.get(_normalize(muscle))
        if state is None:
            return 1.0
        return state.multiplier


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _normalize(muscle: str | None) -> str:
    """把任意写法的肌群名收敛到标准 key，无法识别时原样返回小写。"""
    if not muscle:
        return "full_body"
    return str(muscle).strip().lower()


def halflife_for(muscle: str) -> float:
    return MUSCLE_HALFLIFE_HOURS.get(_normalize(muscle), DEFAULT_HALFLIFE_HOURS)


def capacity_for(muscle: str) -> float:
    return MUSCLE_CAPACITY.get(_normalize(muscle), DEFAULT_CAPACITY)


def label_for(muscle: str) -> str:
    return MUSCLE_LABELS.get(_normalize(muscle), _normalize(muscle))


def stimulus(work: MuscleWork) -> float:
    """把一次动作记录折算成有效容量。

    抗阻：`组数 × 次数 / 10`（3 组 ×10 次 = 3 个单位）
    计时：`秒 / 60`（60 秒 = 1 个单位）
    动作质量只做 ±10% 的轻微调制。
    """
    sets = max(0, int(work.sets or 0))
    reps = max(0, int(work.reps or 0))
    seconds = max(0.0, float(work.seconds or 0.0))

    base = sets * reps / 10.0 + seconds / 60.0
    if base <= 0:
        return 0.0

    if work.form_score is None:
        return base
    score = _clamp(float(work.form_score), 0.0, 100.0)
    return base * (0.9 + 0.002 * score)


def decay(hours: float, halflife: float) -> float:
    """一阶动力学衰减系数；负数时间（时钟回拨 / 脏数据）按 0 处理。"""
    if hours <= 0 or halflife <= 0:
        return 1.0 if hours <= 0 else 0.0
    return 0.5 ** (hours / halflife)


def hours_between(now: datetime, then: datetime) -> float:
    return max(0.0, (now - then).total_seconds() / 3600.0)


# --------------------------------------------------------------------------- #
# 核心计算
# --------------------------------------------------------------------------- #


def _contributions(work: MuscleWork) -> list[tuple[str, float]]:
    """把一次记录摊到主目标肌群与协同肌上，返回 `(肌群, 加权刺激量)`。"""
    base = stimulus(work)
    if base <= 0:
        return []

    primary = _normalize(work.muscle)
    result = [(primary, base)]
    for other, weight in MUSCLE_SYNERGY.get(primary, {}).items():
        if weight > 0:
            result.append((_normalize(other), base * weight))
    return result


def residual_fatigue(works: Iterable[MuscleWork], muscle: str, now: datetime) -> float:
    """某个肌群在 `now` 时刻的残余疲劳。"""
    target = _normalize(muscle)
    halflife = halflife_for(target)
    total = 0.0
    for work in works:
        for key, amount in _contributions(work):
            if key != target:
                continue
            total += amount * decay(hours_between(now, work.at), halflife)
    return total


def weekly_sets(works: Iterable[MuscleWork], muscle: str, now: datetime, days: float = 7.0) -> float:
    """回看 `days` 天、只统计主目标肌群的组数（协同肌不计入容量）。"""
    target = _normalize(muscle)
    cutoff = now - timedelta(days=days)
    total = 0.0
    for work in works:
        if _normalize(work.muscle) != target:
            continue
        if work.at < cutoff or work.at > now:
            continue
        total += max(0, int(work.sets or 0))
    return total


def recovery_percent(residual: float, capacity: float) -> float:
    """残余疲劳 → 恢复度（0-100）。"""
    if capacity <= 0:
        return 100.0
    return _clamp(100.0 * (1.0 - residual / capacity), 0.0, 100.0)


def status_for(recovery: float) -> str:
    if recovery >= READY_THRESHOLD:
        return "ready"
    if recovery >= FATIGUED_THRESHOLD:
        return "caution"
    return "fatigued"


def volume_status_for(sets: float) -> str:
    if sets <= 0:
        return "idle"
    if sets < WEEKLY_SETS_MIN:
        return "under"
    if sets <= WEEKLY_SETS_MAX:
        return "optimal"
    return "over"


def hours_to_ready(residual: float, capacity: float, halflife: float) -> float:
    """还需要多少小时才能回到 `READY_THRESHOLD` 以上。"""
    target_residual = capacity * (1.0 - READY_THRESHOLD / 100.0)
    if residual <= target_residual:
        return 0.0
    if halflife <= 0:
        return 0.0
    ratio = residual / target_residual
    if ratio <= 1.0:
        return 0.0
    return halflife * math.log2(ratio)


def multiplier_for_recovery(recovery: float) -> float:
    """恢复度 → 推荐加权（0.55 - 1.15）。"""
    return MULTIPLIER_MIN + MULTIPLIER_SPAN * _clamp(recovery, 0.0, 100.0) / 100.0


def muscle_state(works: Sequence[MuscleWork], muscle: str, now: datetime) -> MuscleState:
    target = _normalize(muscle)
    residual = residual_fatigue(works, target, now)
    capacity = capacity_for(target)
    recovery = recovery_percent(residual, capacity)
    sets = weekly_sets(works, target, now)
    return MuscleState(
        muscle=target,
        label=label_for(target),
        residual=residual,
        recovery=recovery,
        status=status_for(recovery),
        hours_to_ready=hours_to_ready(residual, capacity, halflife_for(target)),
        weekly_sets=sets,
        volume_status=volume_status_for(sets),
        multiplier=multiplier_for_recovery(recovery),
    )


def muscle_recovery(
    works: Iterable[MuscleWork],
    now: datetime,
    muscles: Iterable[str] | None = None,
) -> RecoverySnapshot:
    """计算全部（或指定）肌群的恢复快照，并给出今日建议。

    `focus` 优先挑"恢复完全 + 本周容量还没到上限"的肌群；
    `avoid` 是仍在酸痛窗口内的肌群。
    """
    items = list(works)
    keys = [ _normalize(m) for m in muscles ] if muscles is not None else list(MUSCLE_ORDER)

    states: dict[str, MuscleState] = {}
    for key in keys:
        states[key] = muscle_state(items, key, now)

    ready = [state for state in states.values() if state.status == "ready"]
    # 容量已经过量的肌群不该再被"推荐"，除非实在没有别的可练。
    candidates = [state for state in ready if state.volume_status != "over"]
    if not candidates:
        candidates = ready

    candidates.sort(
        key=lambda state: (
            -state.recovery,
            state.weekly_sets,
        )
    )
    focus = [state.muscle for state in candidates[:2]]
    avoid = [
        state.muscle
        for state in sorted(states.values(), key=lambda item: item.recovery)
        if state.status == "fatigued"
    ]
    return RecoverySnapshot(muscles=states, focus=focus, avoid=avoid)


def rebalance_multipliers(snapshot: RecoverySnapshot) -> Mapping[str, float]:
    """给推荐重排用的 `{肌群: 加权}` 映射。"""
    return {key: state.multiplier for key, state in snapshot.muscles.items()}
