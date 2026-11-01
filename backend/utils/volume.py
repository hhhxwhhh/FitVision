"""训练容量引擎（Volume / 容量结构分析，纯 Python，无 Django 依赖）。

现有的"训练量"全部是**算术吨位**：`Σ(重量 × 次数)`。这个口径有两个硬伤：

1. **被极端组主导。** 一次 1RM 试举（100kg × 1）贡献 100kg·次，
   和一次 40kg × 12 的常规组贡献 480kg·次 —— 后者才是真正的训练量，
   但只要多做两次大重量试举，算术和就会翻倍，而身体并没有多受多少刺激。
   事实上训练效果对"每次刺激的贡献"是**次线性**的：同样的容量，
   分成更多组比集中在少数组更有效（这正是"容量分散原则"的物理基础）。
2. **不区分强度。** 同样 5000kg·次，分布在 60% 1RM 和 90% 1RM 上，
   适应方向完全不同（前者偏耐力/肌肥大，后者偏力量/神经适应）。

本引擎用三个更稳健的量替换算术吨位：

1. **强度加权容量（Intensity-Weighted Volume, IWV）**
   每组按其相对强度折算：`容量 × %1RM`。这让"用轻重量做很多次"
   和"用重重量做很少次"能落在同一个可比尺度上，也自然与
   `utils.trimp` 的强度区间共用同一套口径。

2. **幂平均有效容量（Power-Mean Effective Volume）**
   用 **幂平均（generalized mean / Hölder mean）** 代替算术和：
   `M_p = (Σ xᵢᵖ / n)^(1/p)`。`p = 1` 是算术平均（传统口径），
   `p → 0` 趋近**几何平均**，对极端值极不敏感。
   本引擎取 **p = 0.5**（平方根平均，介于两者之间）：
   既不会让一次试举毁掉整周数据，又不会完全抹掉组间差异。
   这就是"有效容量" —— 一次训练真正贡献了多少"可持续的刺激"。

3. **容量集中度（Gini 系数）**
   把容量按肌群摊开，算 **Gini 系数**：0 表示完全均匀，
   接近 1 表示全挤在一个地方。训练容量高度集中意味着
   发展肌群不平衡、代偿模式固化，是伤病常见的前兆。

此外还给出**周容量趋势**：用 **对数空间的 Theil–Sen 稳健斜率**
（所有点对斜率的中位数）代替最小二乘 —— 最小二乘会被一次异常周带跑，
Theil–Sen 的崩溃点约 29%，异常周只影响局部而不会翻转整段趋势。

> 小样本提示：Theil–Sen 的稳健性在样本充足时最明显。点数少于 5 时，
> 一次异常周仍会明显影响斜率 —— 引擎因此要求至少 `MIN_TREND_WEEKS` 周
> 才会给出趋势标签，否则返回 `unknown`。

**与其他引擎的关系**：

- `utils.trimp` 回答"强度分布对不对"；
- `utils.readiness` 回答"我今天状态好不好"；
- `utils.recovery` 回答"某个肌群恢复了吗"；
- **本引擎回答"容量的量与结构对不对"** —— 四者互补，不重复。
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from utils.trimp import SetLoad, resolve_percent

# --------------------------------------------------------------------------- #
# 可调超参
# --------------------------------------------------------------------------- #

#: 幂平均的阶。0 趋近几何平均（最抗离群），1 是算术平均（传统口径）。
#: 取 0.5 —— 平方根平均，兼顾稳健性与区分度。
POWER_MEAN_ORDER = 0.5

#: 容量集中度（肌群 Gini）超过该值即判定为"结构失衡"。
CONCENTRATION_WARN = 0.55

#: 单周有效容量相对历史中位数的变动幅度，超过该比例视为显著变化。
WEEKLY_CHANGE_NOTABLE = 0.15

#: 判定"容量在涨 / 在跌 / 稳定"的对数斜率阈值（每周）。
TREND_UP = 0.02
TREND_DOWN = -0.02

#: 参与趋势判断所需的最少周数。
MIN_TREND_WEEKS = 3

#: 每个肌群**每周平均**有效容量的参考区间（单位：强度加权 kg·次）。
#: 下界来自"最低有效刺激"，上界来自"超过后收益递减、疲劳累积"。
#: 这是一个粗略的标定值：典型肌群一周 4–8 组、每组 60–100kg 时
#: 落在 1500–6000 区间内，久经训练的腿/胸可以更高。
MUSCLE_VOLUME_FLOOR = 1500.0
MUSCLE_VOLUME_CEILING = 12000.0

#: 肌群标签（与 `utils.recovery.MUSCLE_LABELS` 保持一致的口径）。
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


# --------------------------------------------------------------------------- #
# 基础工具
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def power_mean(values: Sequence[float], order: float = POWER_MEAN_ORDER) -> float:
    """幂平均（generalized mean / Hölder mean）。

    `order = 1` 是算术平均，`order → 0` 趋近几何平均，
    `order = 2` 是均方根。`order = 0` 直接按几何平均的极限式计算。

    空序列返回 0。
    """
    items = [float(v) for v in values if v is not None]
    if not items:
        return 0.0
    if abs(order) < 1e-9:
        # 几何平均的极限式：exp(mean(ln x))。负数无定义，跳过。
        positives = [v for v in items if v > 0]
        if not positives:
            return 0.0
        return math.exp(sum(math.log(v) for v in positives) / len(positives))
    if any(v < 0 for v in items):
        raise ValueError("幂平均不支持负值")
    return (sum(v**order for v in items) / len(items)) ** (1.0 / order)


def gini(values: Sequence[float]) -> float:
    """Gini 系数（基尼系数），衡量分布的集中程度。

    0 表示完全均匀（所有值相等），接近 1 表示极端集中。
    用的是标准的排序加权公式，`n = 1` 时返回 0
    （单个观测点按定义不存在离散度）。

    注意：这个函数度量的是"**给定集合内部**的离散程度"。
    如果只统计练过的肌群，那么"只练胸"会得到 0 —— 看起来很均匀，
    其实是最极端的失衡。所以 `volume_report` 在只练了一个肌群时
    单独把集中度置为 1.0。
    """
    items = sorted(float(v) for v in values if v is not None and v >= 0)
    n = len(items)
    if n <= 1:
        return 0.0
    total = sum(items)
    if total <= 0:
        return 0.0
    weighted = sum((index + 1) * value for index, value in enumerate(items))
    return _clamp((2.0 * weighted) / (n * total) - (n + 1.0) / n, 0.0, 1.0)


def theil_sen_slope(values: Sequence[float]) -> float:
    """Theil–Sen 稳健斜率（所有点对斜率的中位数）。

    最小二乘会被离群点拽跑（一次超长训练周就能让整条趋势线倾斜），
    Theil–Sen 取所有点对斜率的中位数，崩溃点约 29% ——
    近三成的数据是异常值也不会翻转结论。

    样本少于 2 个时返回 0。

    小样本注意：`n` 越小，被离群点影响的点对占比越高。
    `n = 4` 时有 3/6 的点对涉及离群点，中位数仍会被明显拉高；
    `n ≥ 8` 之后才真正体现出稳健性。
    """
    items = [float(v) for v in values if v is not None]
    n = len(items)
    if n < 2:
        return 0.0
    slopes: list[float] = []
    for i in range(n - 1):
        for j in range(i + 1, n):
            delta = j - i
            if delta > 0:
                slopes.append((items[j] - items[i]) / delta)
    if not slopes:
        return 0.0
    slopes.sort()
    mid = len(slopes) // 2
    if len(slopes) % 2 == 1:
        return slopes[mid]
    return (slopes[mid - 1] + slopes[mid]) / 2.0


def _normalize_muscle(muscle: str | None) -> str:
    """把肌群名收敛到标准 key，无法识别时归到 ``full_body``。"""
    if not muscle:
        return "full_body"
    key = str(muscle).strip().lower()
    return key if key in MUSCLE_LABELS else "full_body"


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class SetVolume:
    """一组的容量信息。

    与 `utils.trimp.SetLoad` 的区别是这里额外带 `muscle` ——
    容量引擎要做肌群维度的结构分析。
    """

    reps: int = 0
    weight: float = 0.0
    percent: float | None = None
    rpe: float | None = None
    e1rm: float = 0.0
    muscle: str = "full_body"

    @property
    def is_measurable(self) -> bool:
        """该组能否参与强度加权。

        自重动作（无重量、算不出强度）算不出"强度加权容量"，
        但它仍然做了功 —— 所以用这个属性区分"可计量"与"有贡献"。
        """
        return self.reps > 0 and self.weight > 0

    @property
    def tonnage(self) -> float:
        """传统算术吨位（kg·次）。"""
        return float(self.weight) * float(self.reps)

    @property
    def intensity_volume(self) -> float:
        """强度加权容量：`吨位 × %1RM / 100`。

        优先用已知的强度百分比；没有就用重量 + e1RM 反推；
        两者都没有（纯自重）时按 0 计入 —— 这类组的贡献由
        `tonnage` 单独体现，不混进强度加权口径。
        """
        percent = resolve_percent(
            SetLoad(
                reps=self.reps,
                weight=self.weight,
                percent=self.percent,
                rpe=self.rpe,
                e1rm=self.e1rm,
            )
        )
        if percent is None or percent <= 0:
            return 0.0
        return self.tonnage * (percent / 100.0)


@dataclass(frozen=True)
class SessionSets:
    """一次训练的原始组数据（带日期）。

    容量引擎需要"按周聚合"的能力，所以保留原始组数据，
    而不只是预先算好的汇总值。
    """

    date: date | None
    sets: tuple[SetVolume, ...] = ()

    def volume(self) -> SessionVolume:
        """算出这次训练的容量汇总。"""
        return session_volume(self.sets, day=self.date)


@dataclass(frozen=True)
class SessionVolume:
    """一次训练的容量结构。"""

    date: date | None
    sets: int
    measurable_sets: int
    tonnage: float
    intensity_volume: float
    effective_volume: float

    def as_dict(self) -> dict:
        return {
            "date": self.date.isoformat() if self.date else None,
            "sets": self.sets,
            "measurable_sets": self.measurable_sets,
            "tonnage": round(self.tonnage, 1),
            "intensity_volume": round(self.intensity_volume, 1),
            "effective_volume": round(self.effective_volume, 1),
        }


@dataclass(frozen=True)
class MuscleVolume:
    """单个肌群的容量结构（数值为**每周平均**）。"""

    muscle: str
    label: str
    sets: int
    tonnage: float
    intensity_volume: float
    effective_volume: float
    weeks: int = 1

    def as_dict(self, total_effective: float = 0.0) -> dict:
        share = (self.effective_volume / total_effective) if total_effective > 0 else 0.0
        return {
            "muscle": self.muscle,
            "label": self.label,
            "sets": self.sets,
            "weeks": self.weeks,
            "tonnage": round(self.tonnage, 1),
            "intensity_volume": round(self.intensity_volume, 1),
            "effective_volume": round(self.effective_volume, 1),
            "share": round(share, 3),
            "status": self.status(total_effective),
        }

    def status(self, total_effective: float = 0.0) -> str:
        """该肌群的容量状态。

        依据"每周平均有效容量是否落在参考区间内"给出
        `low` / `ok` / `high`，`unknown` 表示总量不足无法判定。
        """
        if total_effective <= 0:
            return "unknown"
        if self.effective_volume < MUSCLE_VOLUME_FLOOR:
            return "low"
        if self.effective_volume > MUSCLE_VOLUME_CEILING:
            return "high"
        return "ok"


@dataclass(frozen=True)
class VolumeReport:
    """一段时间的容量结构汇总。"""

    sessions: tuple[SessionVolume, ...]
    weekly: tuple[dict, ...]
    muscles: tuple[MuscleVolume, ...]
    total_tonnage: float
    total_intensity_volume: float
    total_effective_volume: float
    concentration: float
    trend_slope: float
    trend: str
    verdict: str
    advice: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        total = self.total_effective_volume
        return {
            "sessions": [session.as_dict() for session in self.sessions],
            "weekly": list(self.weekly),
            "muscles": [muscle.as_dict(total) for muscle in self.muscles],
            "total_tonnage": round(self.total_tonnage, 1),
            "total_intensity_volume": round(self.total_intensity_volume, 1),
            "total_effective_volume": round(self.total_effective_volume, 1),
            "concentration": round(self.concentration, 3),
            "trend_slope": round(self.trend_slope, 4),
            "trend": self.trend,
            "verdict": self.verdict,
            "advice": list(self.advice),
        }


# --------------------------------------------------------------------------- #
# 单次训练
# --------------------------------------------------------------------------- #


def session_volume(
    sets: Sequence[SetVolume], day: date | None = None
) -> SessionVolume:
    """算一次训练的容量。

    `effective_volume` 是该次训练所有可计量组的**幂平均**再乘以组数 ——
    换句话说，它回答"如果这次训练每一组都和'典型组'一样有效，
    总共能得到多少有效容量"。

    关键性质：一个极端组的**边际贡献不会超过它自己的原始值**，
    因此一次 1RM 试举不会让有效容量暴涨；而算术吨位会。
    """
    measurable = [item for item in sets if item.is_measurable]
    tonnage = sum(item.tonnage for item in sets)
    intensity_volume = sum(item.intensity_volume for item in measurable)
    effective = power_mean(
        [item.intensity_volume for item in measurable if item.intensity_volume > 0],
        POWER_MEAN_ORDER,
    ) * len(measurable)
    return SessionVolume(
        date=day,
        sets=len(sets),
        measurable_sets=len(measurable),
        tonnage=tonnage,
        intensity_volume=intensity_volume,
        effective_volume=effective,
    )


# --------------------------------------------------------------------------- #
# 肌群维度
# --------------------------------------------------------------------------- #


def muscle_volumes(sets: Sequence[SetVolume]) -> tuple[MuscleVolume, ...]:
    """把一组训练记录摊到各肌群上，算容量结构。

    组数与吨位按主目标肌群归属（不做协同肌分摊），
    与 `utils.recovery.weekly_sets` 的口径一致 —— 两处保持一致，
    用户看到的"本周练了多少"才不会自相矛盾。

    返回值是这批记录**整体**的容量；跨周取平均由 `volume_report` 负责。
    """
    buckets: dict[str, list[SetVolume]] = {}
    for item in sets:
        buckets.setdefault(_normalize_muscle(item.muscle), []).append(item)

    result: list[MuscleVolume] = []
    for muscle, items in buckets.items():
        measurable = [item for item in items if item.is_measurable]
        intensity_volume = sum(item.intensity_volume for item in measurable)
        effective = power_mean(
            [item.intensity_volume for item in measurable if item.intensity_volume > 0],
            POWER_MEAN_ORDER,
        ) * len(measurable)
        result.append(
            MuscleVolume(
                muscle=muscle,
                label=MUSCLE_LABELS.get(muscle, muscle),
                sets=len(items),
                tonnage=sum(item.tonnage for item in items),
                intensity_volume=intensity_volume,
                effective_volume=effective,
            )
        )
    result.sort(key=lambda item: item.effective_volume, reverse=True)
    return tuple(result)


def _iso_week(day: date) -> tuple[int, int]:
    iso = day.isocalendar()
    return (iso[0], iso[1])


def average_muscle_volumes(
    sessions: Sequence[SessionSets],
) -> tuple[MuscleVolume, ...]:
    """把多次训练的容量按肌群聚合成"每周平均"。

    先按自然周把训练分组，算出每周每肌群的容量，再对周取平均。
    这样"练得多的人"和"练得少的人"的肌群容量可以横向比较 ——
    否则一周练 5 次的人每个肌群的数字天然是练 2 次的人的 2.5 倍。
    """
    weekly_sets: dict[str, list[SetVolume]] = {}
    week_count: dict[str, set[tuple[int, int]]] = {}
    for session in sessions:
        if session.date is None or not session.sets:
            continue
        key = _iso_week(session.date)
        for muscle in {_normalize_muscle(item.muscle) for item in session.sets}:
            week_count.setdefault(muscle, set()).add(key)

    for session in sessions:
        if session.date is None:
            continue
        for item in session.sets:
            weekly_sets.setdefault(_normalize_muscle(item.muscle), []).append(item)

    if not weekly_sets:
        return ()

    result: list[MuscleVolume] = []
    for muscle, items in weekly_sets.items():
        weeks = max(1, len(week_count.get(muscle, set())))
        per_week = muscle_volumes(items)
        target = next((item for item in per_week if item.muscle == muscle), None)
        if target is None:
            continue
        result.append(
            MuscleVolume(
                muscle=muscle,
                label=target.label,
                sets=round(target.sets / weeks),
                tonnage=target.tonnage / weeks,
                intensity_volume=target.intensity_volume / weeks,
                effective_volume=target.effective_volume / weeks,
                weeks=weeks,
            )
        )
    result.sort(key=lambda item: item.effective_volume, reverse=True)
    return tuple(result)


# --------------------------------------------------------------------------- #
# 周汇总
# --------------------------------------------------------------------------- #


def weekly_summary(
    sessions: Sequence[SessionVolume], weeks: int = 4
) -> tuple[dict, ...]:
    """按自然周汇总容量（最近 `weeks` 周，从早到晚）。"""
    buckets: dict[tuple[int, int], list[SessionVolume]] = {}
    for session in sessions:
        if session.date is None:
            continue
        buckets.setdefault(_iso_week(session.date), []).append(session)

    ordered = sorted(buckets.items())[-max(1, weeks):]
    summary: list[dict] = []
    for (year, week), items in ordered:
        summary.append(
            {
                "year": year,
                "week": week,
                "sessions": len(items),
                "sets": sum(item.sets for item in items),
                "measurable_sets": sum(item.measurable_sets for item in items),
                "tonnage": round(sum(item.tonnage for item in items), 1),
                "intensity_volume": round(
                    sum(item.intensity_volume for item in items), 1
                ),
                "effective_volume": round(
                    sum(item.effective_volume for item in items), 1
                ),
            }
        )
    return tuple(summary)


def trend_label(slope: float) -> str:
    """把对数斜率翻译成趋势标签。

    斜率是在**对数空间**上算的（每周的相对变化率），
    所以 0.02 表示"每周约 +2%"。
    """
    if slope >= TREND_UP:
        return "rising"
    if slope <= TREND_DOWN:
        return "falling"
    return "steady"


def weekly_trend(weekly: Sequence[dict]) -> float:
    """周有效容量的对数空间 Theil–Sen 斜率。

    先取 log（让"增长 50%"和"下跌 33%"在尺度上对称），
    再算稳健斜率 —— 这样一次异常的高容量周不会翻转整段趋势。
    """
    values = [float(item.get("effective_volume") or 0.0) for item in weekly]
    positives = [value for value in values if value > 0]
    if len(positives) < MIN_TREND_WEEKS:
        return 0.0
    logs = [math.log(value) for value in positives]
    return theil_sen_slope(logs)


# --------------------------------------------------------------------------- #
# 总报告
# --------------------------------------------------------------------------- #


def _concentration(muscles: Sequence[MuscleVolume]) -> float:
    """容量集中度，归一化到 0–1。

    只统计**练过的**肌群 —— 否则"练了胸背腿三块"会因为其余五块为 0
    而显得极度失衡（这正是普通 Gini 直接套用的陷阱）。

    但如果只练了一个肌群，Gini 按定义返回 0（单一观测点没有离散度），
    而这恰恰是最极端的失衡 —— 所以单独置为 1.0。

    还要按组数归一化：Gini 的理论上限是 `(n-1)/n`，
    两个肌群最多只能到 0.5，三个最多 0.667。若不归一化，
    同一个阈值对"练两块"和"练七块"含义完全不同。
    归一化后 1.0 一律表示"完全集中在一个地方"，阈值才有统一意义。
    """
    trained = [item for item in muscles if item.effective_volume > 0]
    if not trained:
        return 0.0
    if len(trained) == 1:
        return 1.0
    max_gini = (len(trained) - 1) / len(trained)
    if max_gini <= 0:
        return 0.0
    return _clamp(gini([item.effective_volume for item in trained]) / max_gini, 0.0, 1.0)


def volume_report(
    sessions: Sequence[SessionSets],
    weeks: int = 4,
) -> VolumeReport:
    """汇总一段时间的容量结构，给出结论与建议。"""
    ordered_sessions = sorted(
        (item for item in sessions if item.date is not None),
        key=lambda item: item.date,
    )
    volumes = [item.volume() for item in ordered_sessions]
    weekly = weekly_summary(volumes, weeks=weeks)
    muscles = average_muscle_volumes(ordered_sessions)

    total_tonnage = sum(item.tonnage for item in volumes)
    total_intensity = sum(item.intensity_volume for item in volumes)
    total_effective = sum(item.effective_volume for item in volumes)

    concentration = _concentration(muscles)
    slope = weekly_trend(weekly)
    trend = trend_label(slope) if len(weekly) >= MIN_TREND_WEEKS else "unknown"

    if total_effective <= 0:
        return VolumeReport(
            sessions=tuple(volumes),
            weekly=weekly,
            muscles=muscles,
            total_tonnage=total_tonnage,
            total_intensity_volume=total_intensity,
            total_effective_volume=0.0,
            concentration=0.0,
            trend_slope=0.0,
            trend="unknown",
            verdict="数据不足",
            advice=(
                "还没有带重量或 RPE 的训练记录，补上重量后就能看到容量结构。",
            ),
        )

    # 肌群容量状态判定用的分母：所有练过的肌群每周平均之和
    muscle_total = sum(item.effective_volume for item in muscles)

    advice: list[str] = []

    # 1) 容量结构是否集中
    if concentration > CONCENTRATION_WARN:
        top = muscles[0] if muscles else None
        if top is not None:
            if len(muscles) == 1:
                advice.append(
                    f"这段时间的容量全在{top.label}，其他部位完全没有刺激，"
                    "建议把训练摊到更多肌群。"
                )
            else:
                advice.append(
                    f"容量高度集中在{top.label}（集中度 {concentration:.2f}），"
                    "其他部位被挤掉了，容易形成代偿模式。"
                )
    elif len(muscles) <= 1:
        advice.append("只记录到一个肌群的容量，试着把全身都练一遍再看结构。")

    # 2) 是否有肌群明显欠练 / 过练
    low = [item for item in muscles if item.status(muscle_total) == "low"]
    high = [item for item in muscles if item.status(muscle_total) == "high"]
    if low:
        names = "、".join(item.label for item in low[:3])
        advice.append(f"{names} 的每周有效容量偏低，可以适当加量。")
    if high:
        names = "、".join(item.label for item in high[:3])
        advice.append(f"{names} 的每周有效容量偏高，注意恢复和关节压力。")

    # 3) 趋势
    if trend == "rising":
        advice.append("有效容量在稳步上升，保持这个节奏就行，别急着继续加。")
    elif trend == "falling":
        advice.append("有效容量在往下走，检查是不是漏记了训练或者强度掉太多。")
    elif trend == "steady":
        advice.append("容量基本持平，可以考虑小幅加量或调整强度分布打破平台。")

    # 4) 单周突变提醒（用中位数做基准，避免被本周自己带偏）
    if len(weekly) >= 3:
        medians = sorted(
            float(item.get("effective_volume") or 0.0) for item in weekly
        )
        median = medians[len(medians) // 2]
        latest = float(weekly[-1].get("effective_volume") or 0.0)
        if median > 0:
            change = (latest - median) / median
            if abs(change) >= WEEKLY_CHANGE_NOTABLE:
                if change > 0:
                    advice.append("本周有效容量明显高于往常，注意别一次性加太猛。")
                else:
                    advice.append("本周有效容量明显低于往常，确认一下是不是漏记了。")

    verdict = _verdict(concentration, trend, total_effective)
    return VolumeReport(
        sessions=tuple(volumes),
        weekly=weekly,
        muscles=muscles,
        total_tonnage=total_tonnage,
        total_intensity_volume=total_intensity,
        total_effective_volume=total_effective,
        concentration=concentration,
        trend_slope=slope,
        trend=trend,
        verdict=verdict,
        advice=tuple(advice),
    )


def _verdict(concentration: float, trend: str, total_effective: float) -> str:
    """给容量结构下一个简短结论。"""
    if total_effective <= 0:
        return "数据不足"
    if concentration > CONCENTRATION_WARN:
        return "容量结构失衡"
    if trend == "rising":
        return "容量稳步上升"
    if trend == "falling":
        return "容量有所下滑"
    if trend == "steady":
        return "容量平稳"
    return "容量结构正常"


def summarize_by_muscle(sets: Iterable[SetVolume]) -> list[dict]:
    """便捷入口：直接给出各肌群的容量字典列表。"""
    muscles = muscle_volumes(list(sets))
    total = sum(item.effective_volume for item in muscles)
    return [item.as_dict(total) for item in muscles]
