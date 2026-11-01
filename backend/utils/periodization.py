"""训练周期化引擎（纯 Python，无 Django 依赖）。

前面三个引擎各自回答一个"横截面"的问题：

- `utils.readiness`：今天整体状态怎么样（能不能练）。
- `utils.recovery`：今天该练哪个部位（局部恢复）。
- `utils.strength`：这一组该上多少重量（渐进超负荷）。

但真实的训练计划是**时间轴**上的问题：一个中周期（mesocycle，3–6 周）里，
容量与强度应该怎么起伏，什么时候该退峰，什么时候该减量。这个模块补上这一层。

模型思路（周期化模型的工程化简化）：

1. **阶段划分**
   经典周期化把中周期拆成四个阶段，本引擎沿用这套结构：

   - `accumulation`（积累）：容量最高、强度最低，用 8–12 次发展肌肉与动作模式。
   - `intensification`（强化）：容量下降、强度上升，6–8 次���向力量。
   - `realization`（实现）：容量最低、强度最高，3–5 次测试真实能力。
   - `deload`（减量）：容量砍半、强度回落，让身体把适应真正吸收掉。

2. **容量来自恢复模型**
   每个肌群有"每周有效组数"目标区间（10–20 组）。已经完成的组数由
   `utils.recovery` 给出，剩余容量 = 目标 − 已完成。再乘以阶段容量系数，
   得到这一周该肌群实际要做的组数。

3. **强度来自力量模型**
   每个动作的最佳 e1RM 来自 `utils.strength`。阶段强度系数决定用 e1RM 的百分之几，
   再经由 `rep_percentage(reps, rir)` 得到具体百分比，最后向下取整到配重片间隔。

4. **分配到训练日**
   肌群按动作模式分组（推 / 拉 / 腿 / 核心），一周内的训练日轮流取组，
   同一肌群不会连续两天练——这与 `utils.recovery` 的半衰期一致。

所有阈值集中在文件头部，便于调参与写进文档。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

# --------------------------------------------------------------------------- #
# 可调超参
# --------------------------------------------------------------------------- #

#: 阶段定义：容量系数、强度系数（占 e1RM 的比例）、次数区间、标题、说明。
PHASES: dict[str, dict] = {
    "accumulation": {
        "label": "积累",
        "volume": 1.0,
        "intensity": 0.72,
        "reps_low": 8,
        "reps_high": 12,
        "rir": 3,
        "note": "容量最高、强度最低，打基础并打磨动作模式",
    },
    "intensification": {
        "label": "强化",
        "volume": 0.85,
        "intensity": 0.82,
        "reps_low": 6,
        "reps_high": 8,
        "rir": 2,
        "note": "容量下调、强度上升，把重量推起来",
    },
    "realization": {
        "label": "实现",
        "volume": 0.7,
        "intensity": 0.92,
        "reps_low": 3,
        "reps_high": 5,
        "rir": 1,
        "note": "峰值阶段，用最少的组数验证最大力量",
    },
    "deload": {
        "label": "减量",
        "volume": 0.5,
        "intensity": 0.6,
        "reps_low": 6,
        "reps_high": 10,
        "rir": 3,
        "note": "容量砍半、强度回落，让身体吸收前面的适应",
    },
}

#: 常见中周期长度对应的阶段序列。
PHASE_TEMPLATES: dict[int, tuple[str, ...]] = {
    1: ("accumulation",),
    2: ("intensification", "realization"),
    3: ("accumulation", "intensification", "realization"),
    4: ("accumulation", "accumulation", "intensification", "realization"),
    5: ("accumulation", "accumulation", "intensification", "realization", "deload"),
    6: ("accumulation", "accumulation", "intensification", "intensification", "realization", "deload"),
}

#: 每个肌群每周的有效组数目标（取 10–20 区间的经验中值）。
MUSCLE_WEEKLY_TARGET: dict[str, float] = {
    "legs": 16.0,
    "glutes": 14.0,
    "back": 16.0,
    "chest": 12.0,
    "shoulders": 12.0,
    "arms": 10.0,
    "abs": 12.0,
}

#: 肌群 → 动作模式分组，用来把训练量分配到不同训练日。
MUSCLE_GROUPS: dict[str, tuple[str, ...]] = {
    "push": ("chest", "shoulders", "arms"),
    "pull": ("back", "arms"),
    "legs": ("legs", "glutes"),
    "core": ("abs",),
}

#: 训练日名称，按天序排布。
DAY_LABELS: tuple[str, ...] = ("第 1 天", "第 2 天", "第 3 天", "第 4 天", "第 5 天", "第 6 天")

#: 每周训练的天数上限。
MAX_DAYS_PER_WEEK = 5

#: 恢复度低于该值时，整体容量再打一个折扣（自动调节）。
AUTOREGULATION_THRESHOLD = 70.0
#: 自动调节时的最小容量折扣（保留 60% 容量，宁可少练也不要带伤硬上）。
AUTOREGULATION_MIN_FACTOR = 0.6


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class MuscleSlot:
    """一个肌群在某个训练日的安排。"""

    muscle: str
    label: str
    sets: int
    reps: int
    weight: float
    e1rm: float
    based_on_e1rm: bool
    note: str

    def as_dict(self) -> dict:
        return {
            "muscle": self.muscle,
            "label": self.label,
            "sets": self.sets,
            "reps": self.reps,
            "weight": round(self.weight, 1),
            "e1rm": round(self.e1rm, 1),
            "based_on_e1rm": self.based_on_e1rm,
            "note": self.note,
        }


@dataclass(frozen=True)
class DayPlan:
    """训练日的安排。"""

    index: int
    label: str
    focus: tuple[str, ...]
    slots: tuple[MuscleSlot, ...]

    @property
    def total_sets(self) -> int:
        return sum(slot.sets for slot in self.slots)

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "label": self.label,
            "focus": list(self.focus),
            "slots": [slot.as_dict() for slot in self.slots],
            "total_sets": self.total_sets,
        }


@dataclass(frozen=True)
class WeekPlan:
    """中周期中的一周。"""

    index: int
    phase: str
    label: str
    note: str
    volume: float
    intensity: float
    reps_low: int
    reps_high: int
    rir: int
    sessions: tuple[DayPlan, ...]

    @property
    def total_sets(self) -> int:
        return sum(day.total_sets for day in self.sessions)

    def as_dict(self) -> dict:
        return {
            "index": self.index,
            "phase": self.phase,
            "label": self.label,
            "note": self.note,
            "volume": round(self.volume, 3),
            "intensity": round(self.intensity, 3),
            "reps_low": self.reps_low,
            "reps_high": self.reps_high,
            "rir": self.rir,
            "total_sets": self.total_sets,
            "sessions": [day.as_dict() for day in self.sessions],
        }


@dataclass(frozen=True)
class Mesocycle:
    """一个完整的中周期。"""

    weeks: tuple[WeekPlan, ...]
    days_per_week: int
    readiness: float = 100.0
    focus: tuple[str, ...] = ()
    avoid: tuple[str, ...] = ()
    autoregulation: float = 1.0
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict:
        return {
            "weeks": [week.as_dict() for week in self.weeks],
            "days_per_week": self.days_per_week,
            "readiness": round(self.readiness, 1),
            "focus": list(self.focus),
            "avoid": list(self.avoid),
            "autoregulation": round(self.autoregulation, 3),
            "notes": list(self.notes),
            "total_weeks": len(self.weeks),
            "total_sets": sum(week.total_sets for week in self.weeks),
        }


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def phase_sequence(weeks: int) -> tuple[str, ...]:
    """给定中周期长度，返回阶段序列。"""
    count = max(1, min(8, int(weeks or 1)))
    template = PHASE_TEMPLATES.get(count)
    if template:
        return template
    # 超出模板范围时按 6 周模板缩放，保证阶段顺序始终合理。
    base = PHASE_TEMPLATES[6]
    if count <= len(base):
        return base[:count]
    repeats = (count + len(base) - 1) // len(base)
    return tuple((base * repeats)[:count])


def autoregulation_factor(readiness: float) -> float:
    """整体状态不佳时对容量做的自动调节折扣。"""
    score = _clamp(float(readiness or 0.0), 0.0, 100.0)
    if score >= AUTOREGULATION_THRESHOLD:
        return 1.0
    span = AUTOREGULATION_THRESHOLD
    factor = AUTOREGULATION_MIN_FACTOR + (1.0 - AUTOREGULATION_MIN_FACTOR) * (score / span)
    return round(_clamp(factor, AUTOREGULATION_MIN_FACTOR, 1.0), 3)


def _normalize_muscle(muscle: str | None) -> str:
    if not muscle:
        return "full_body"
    return str(muscle).strip().lower()


def _muscle_label(muscle: str) -> str:
    labels = {
        "chest": "胸部",
        "back": "背部",
        "shoulders": "肩部",
        "arms": "手臂",
        "abs": "腹部",
        "legs": "腿部",
        "glutes": "臀部",
        "full_body": "全身",
    }
    return labels.get(muscle, muscle)


def _group_for(muscle: str) -> str:
    for group, members in MUSCLE_GROUPS.items():
        if muscle in members:
            return group
    return "core"


# --------------------------------------------------------------------------- #
# 核心计算
# --------------------------------------------------------------------------- #


def weekly_set_target(muscle: str, weekly_sets: float = 0.0) -> float:
    """该肌群这一周还应该做多少组（目标 − 已完成）。"""
    target = MUSCLE_WEEKLY_TARGET.get(muscle, 12.0)
    remaining = target - max(0.0, float(weekly_sets or 0.0))
    return max(0.0, remaining)


def _strength_index(strength_entries: Sequence[Mapping] | None) -> dict[str, Mapping]:
    """把 `growth.services.strength_history` 的结果压成"肌群 → 最强动作"。"""
    index: dict[str, Mapping] = {}
    for entry in strength_entries or []:
        if not isinstance(entry, Mapping):
            continue
        muscle = _normalize_muscle(entry.get("target_muscle"))
        best = float(entry.get("best") or 0.0)
        if best <= 0:
            continue
        current = index.get(muscle)
        if current is None or best > float(current.get("best") or 0.0):
            index[muscle] = entry
    return index


def _slot_for(
    muscle: str,
    sets: int,
    reps: int,
    rir: int,
    strength_entry: Mapping | None,
    intensity: float,
) -> MuscleSlot:
    """为一个肌群生成具体安排（含重量处方）。"""
    label = _muscle_label(muscle)
    e1rm = 0.0
    weight = 0.0
    based = False
    note = ""

    if strength_entry:
        e1rm = float(strength_entry.get("best") or 0.0)
        points = strength_entry.get("points") or []
        last = points[-1] if points else {}
        last_weight = float(last.get("weight") or 0.0)
        last_reps = int(last.get("reps") or 0)
        if e1rm > 0:
            based = True
            from utils.strength import rep_percentage, round_to_increment  # 局部导入避免循环依赖

            # 次数百分比表给出"用多少 e1RM"，阶段强度系数是这一阶段的上限。
            percentage = min(rep_percentage(reps, rir), intensity)
            percentage = _clamp(percentage, 0.3, 1.0)
            weight = round_to_increment(e1rm * percentage)
            if last_weight > 0:
                note = f"上次 {last_weight:g} kg × {last_reps} 次，按阶段强度折算"
            else:
                note = f"按 e1RM {e1rm:g} kg 的 {percentage * 100:.0f}% 折算"

    return MuscleSlot(
        muscle=muscle,
        label=label,
        sets=int(sets),
        reps=int(reps),
        weight=weight,
        e1rm=e1rm,
        based_on_e1rm=based,
        note=note,
    )


def build_mesocycle(
    muscle_states: Mapping[str, Mapping] | None = None,
    strength_entries: Sequence[Mapping] | None = None,
    weeks: int = 4,
    days_per_week: int = 4,
    readiness: float = 100.0,
) -> Mesocycle:
    """构建一个中周期计划。

    - `muscle_states`：`utils.recovery` 的 `as_dict()["muscles"]`（或同结构的列表），
      每个条目含 `muscle` / `recovery` / `weekly_sets` / `status`。
    - `strength_entries`：`growth.services.strength_history` 的结果，
      每个条目含 `target_muscle` / `best` / `points`。
    - `readiness`：整体准备度（0–100），用于容量自动调节。
    """
    states = _normalize_states(muscle_states)
    strength = _strength_index(strength_entries)
    phases = phase_sequence(weeks)
    days = max(1, min(MAX_DAYS_PER_WEEK, int(days_per_week or 1)))
    factor = autoregulation_factor(readiness)

    notes: list[str] = []
    if factor < 1.0:
        notes.append(f"当前准备度 {readiness:.0f} 分，整体容量下调 {(1 - factor) * 100:.0f}%")

    # 本周该练哪些：先看恢复引擎的 focus，再补上容量不足的肌群。
    focus = _select_focus(states, strength)
    avoid = tuple(
        muscle
        for muscle, state in states.items()
        if str(state.get("status") or "") == "fatigued"
    )
    if avoid:
        notes.append("仍在酸痛窗口的肌群本周降权：" + "、".join(_muscle_label(m) for m in avoid))

    week_plans: list[WeekPlan] = []
    for week_index, phase_key in enumerate(phases):
        phase = PHASES[phase_key]
        volume = phase["volume"] * factor
        intensity = phase["intensity"]
        reps = _phase_reps(phase)

        # 剩余容量按阶段容量系数缩放；第一周用真实剩余量，后续周递减体现周期效应。
        decay = 1.0 - 0.08 * week_index
        per_muscle_sets: dict[str, int] = {}
        for muscle in focus:
            remaining = weekly_set_target(muscle, float(states.get(muscle, {}).get("weekly_sets") or 0.0))
            target = remaining * volume * max(0.4, decay)
            per_muscle_sets[muscle] = int(round(target))

        sessions = _build_days(per_muscle_sets, strength, days, reps, phase["rir"], intensity)
        week_plans.append(
            WeekPlan(
                index=week_index + 1,
                phase=phase_key,
                label=str(phase["label"]),
                note=str(phase["note"]),
                volume=volume,
                intensity=intensity,
                reps_low=int(phase["reps_low"]),
                reps_high=int(phase["reps_high"]),
                rir=int(phase["rir"]),
                sessions=tuple(sessions),
            )
        )

    return Mesocycle(
        weeks=tuple(week_plans),
        days_per_week=days,
        readiness=float(readiness or 0.0),
        focus=tuple(focus),
        avoid=avoid,
        autoregulation=factor,
        notes=tuple(notes),
    )


def _normalize_states(muscle_states: Mapping | Iterable | None) -> dict[str, Mapping]:
    """把恢复引擎的输出统一成"肌群 → 状态字典"。

    支持三种输入：`{"muscles": [...]}` 快照、状态列表、或者"肌群 → 状态"字典。
    """
    result: dict[str, Mapping] = {}
    if not muscle_states:
        return result
    if isinstance(muscle_states, Mapping):
        if "muscles" in muscle_states:
            items = list(muscle_states.get("muscles") or [])
        else:
            items = list(muscle_states.values())
    else:
        items = list(muscle_states)
    for item in items:
        if not isinstance(item, Mapping):
            continue
        muscle = _normalize_muscle(item.get("muscle"))
        if muscle and muscle != "full_body":
            result[muscle] = item
    return result


def _select_focus(states: Mapping[str, Mapping], strength: Mapping[str, Mapping]) -> list[str]:
    """选出本周要练的肌群。

    优先用恢复引擎的"就绪"结论，其次考虑"容量不足"，最后看是否有 e1RM 数据
    （有数据的肌群更容易给出精确重量）。
    """
    fatigued = {
        muscle
        for muscle, state in states.items()
        if str(state.get("status") or "") == "fatigued"
    }
    ready = [
        muscle
        for muscle, state in states.items()
        if str(state.get("status") or "") in {"ready", "caution"}
    ]
    under = [
        muscle
        for muscle, state in states.items()
        if str(state.get("volume_status") or "") == "under"
        and muscle not in fatigued
    ]
    scored: list[tuple[float, str]] = []
    for muscle in set(ready) | set(under):
        if muscle in fatigued:
            continue
        state = states.get(muscle, {})
        recovery = float(state.get("recovery") or 0.0)
        weekly = float(state.get("weekly_sets") or 0.0)
        # 容量缺口最多按 10 组计权：完全没练过的肌群不会因此无限压过刚练过但
        # 还没到周容量上限的肌群。
        volume_gap = min(10.0, max(0.0, MUSCLE_WEEKLY_TARGET.get(muscle, 12.0) - weekly))
        # 有 e1RM 数据的肌群优先：有数据才能给出精确重量，训练价值更高。
        has_data = 20.0 if muscle in strength else 0.0
        scored.append((recovery * 0.6 + volume_gap * 1.5 + has_data, muscle))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return [muscle for _, muscle in scored[:6]]


def _phase_reps(phase: Mapping) -> int:
    """阶段内的目标次数取区间中值。"""
    low = int(phase["reps_low"])
    high = int(phase["reps_high"])
    return max(1, (low + high) // 2)


def _build_days(
    per_muscle_sets: Mapping[str, int],
    strength: Mapping[str, Mapping],
    days: int,
    reps: int,
    rir: int,
    intensity: float,
) -> list[DayPlan]:
    """把各肌群的组数分配到 `days` 个训练日。

    同组肌群（推 / 拉 / 腿 / 核心）尽量排在同一天（它们本来就是一套动作模式），
    不同组落在不同天，避免连续两天刺激同一肌群。当动作模式数量多于训练日时，
    一天会安排多个模式，保证每个被选中的肌群都能排进计划。
    """
    groups: dict[str, list[str]] = {}
    for muscle, sets in per_muscle_sets.items():
        if sets <= 0:
            continue
        groups.setdefault(_group_for(muscle), []).append(muscle)

    group_keys = sorted(groups)
    if not group_keys:
        return []

    # 每个动作模式落到哪一天：按天循环分配，保证所有模式都被覆盖。
    day_groups: dict[int, list[str]] = {}
    for order, group in enumerate(group_keys):
        day_groups.setdefault(order % days, []).append(group)

    plan_days: list[DayPlan] = []
    for day_index in range(days):
        members: list[str] = []
        for group in day_groups.get(day_index, []):
            members.extend(groups.get(group, []))
        muscles = sorted(members)
        if not muscles:
            continue
        slots: list[MuscleSlot] = []
        for muscle in muscles:
            sets = int(per_muscle_sets.get(muscle, 0))
            if sets <= 0:
                continue
            slots.append(
                _slot_for(
                    muscle,
                    sets,
                    reps,
                    rir,
                    strength.get(muscle),
                    intensity,
                )
            )
        if not slots:
            continue
        plan_days.append(
            DayPlan(
                index=day_index + 1,
                label=DAY_LABELS[min(day_index, len(DAY_LABELS) - 1)],
                focus=tuple(muscles),
                slots=tuple(slots),
            )
        )
    return plan_days
