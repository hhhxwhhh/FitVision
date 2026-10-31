"""训练准备度 / 疲劳度引擎（纯 Python，无 Django 依赖）。

这一层刻意保持"纯函数 + 标准库"，好处是：
- 可以脱离 Django 单独跑单测（`python -m unittest utils.test_readiness`）；
- 可以复用到离线分析脚本、数据生成器和未来的 Batch 任务；
- 所有阈值都集中在这里，服务端视图只负责取数与拼装。

模型组合（运动科学里经过验证的三条主线）：

1. **Banister  Fitness-Fatigue 冲激响应模型**
   每一次训练都会同时产生"体能"（衰减慢，τ≈42 天）与"疲劳"（衰减快，τ≈7 天）
   两条指数响应曲线，两者之差即 TSB（Training Stress Balance，训练压力平衡），
   也就是常说的"竞技状态 form"。

2. **ACWR（急性:慢性负荷比，Williams 2017）**
   用 EWMA 而不是简单滑动平均，避免"一周前的负荷突然失效"的悬崖效应。
   0.8–1.3 是公认的甜蜜区，> 1.5 伤病风险显著上升，< 0.8 说明刺激不足。

3. **Foster 单调性 / 紧张度（Monotony & Strain）**
   周负荷的均值/标准差刻画"训练是否过于单一"，两者相乘得到 strain，
   用来给出"换花样"的建议。

再叠加动作质量趋势（最小二乘斜率）与恢复间隔，得到 0-100 的准备度总分。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, Sequence

# --------------------------------------------------------------------------- #
# 可调超参（集中放置，便于调参与写进文档）
# --------------------------------------------------------------------------- #

FITNESS_TAU = 42.0  # 体能响应衰减常数（天）
FATIGUE_TAU = 7.0  # 疲劳响应衰减常数（天）
ACUTE_SPAN = 7  # ACWR 急性窗口
CHRONIC_SPAN = 28  # ACWR 慢性窗口
MONOTONY_WEEKS = 4  # 计算单调性时回看的周数
TREND_WINDOW = 8  # 动作质量趋势使用的会话数
HISTORY_DAYS = 120  # 冲激响应回看窗口（超过 4τ 后贡献可忽略）

ACWR_SWEET_LOW = 0.8
ACWR_SWEET_HIGH = 1.3
ACWR_DANGER = 1.5

MONOTONY_ALERT = 2.0  # Foster 建议超过该值即视为"过于单调"

MIN_SCORE = 20.0
MAX_SCORE = 99.0


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class DailyLoad:
    """某一天聚合后的训练负荷。

    `load` 是无量纲的训练负荷（内部统一为"等效分钟 × 强度系数"），
    `form_score` 为当天会话的平均动作质量（0-100），缺失时传 None。
    """

    day: date
    load: float = 0.0
    minutes: float = 0.0
    form_score: float | None = None


@dataclass(frozen=True)
class ReadinessComponents:
    """拆解后的各项指标，前端可以用来画雷达图或做解释。"""

    acute_load: float
    chronic_load: float
    acwr: float
    fitness: float
    fatigue: float
    tsb: float
    monotony: float
    strain: float
    form_trend: float
    rest_days: int
    weekly_load: float
    weekly_loads: list[float]
    session_count: int

    def as_dict(self) -> dict:
        return {
            "acute_load": round(self.acute_load, 2),
            "chronic_load": round(self.chronic_load, 2),
            "acwr": round(self.acwr, 3),
            "fitness": round(self.fitness, 2),
            "fatigue": round(self.fatigue, 2),
            "tsb": round(self.tsb, 2),
            "monotony": round(self.monotony, 2),
            "strain": round(self.strain, 2),
            "form_trend": round(self.form_trend, 2),
            "rest_days": self.rest_days,
            "weekly_load": round(self.weekly_load, 2),
            "weekly_loads": [round(value, 2) for value in self.weekly_loads],
            "session_count": self.session_count,
        }


@dataclass(frozen=True)
class ReadinessReport:
    """最终对外输出的准备度报告。"""

    score: int
    tone: str  # excellent | good | moderate | recover
    label: str
    advice: str
    intensity: str  # rest | light | moderate | hard
    volume_multiplier: float
    components: ReadinessComponents
    reasons: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        payload = {
            "score": self.score,
            "tone": self.tone,
            "label": self.label,
            "advice": self.advice,
            "intensity": self.intensity,
            "volume_multiplier": round(self.volume_multiplier, 2),
            "reasons": list(self.reasons),
        }
        payload.update(self.components.as_dict())
        return payload


# --------------------------------------------------------------------------- #
# 基础数学工具
# --------------------------------------------------------------------------- #


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def ewma(values: Sequence[float], span: int) -> float:
    """指数移动平均，返回序列末位的平滑值。

    `span` 与 pandas 的 `ewm(span=n)` 语义一致：alpha = 2 / (span + 1)。
    空序列返回 0。
    """
    if not values or span <= 0:
        return 0.0
    alpha = 2.0 / (span + 1.0)
    level = float(values[0])
    for value in values[1:]:
        level = alpha * float(value) + (1.0 - alpha) * level
    return level


def linear_trend(values: Sequence[float]) -> float:
    """最小二乘斜率（每个样本的单位变化量）。样本不足时返回 0。"""
    n = len(values)
    if n < 2:
        return 0.0
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / n
    numerator = sum((i - mean_x) * (v - mean_y) for i, v in enumerate(values))
    denominator = sum((i - mean_x) ** 2 for i in range(n))
    if denominator == 0:
        return 0.0
    return numerator / denominator


def standard_deviation(values: Sequence[float]) -> float:
    """样本标准差（n-1）。样本不足时返回 0，避免单调性除零。"""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return math.sqrt(variance)


# --------------------------------------------------------------------------- #
# 负荷窗口
# --------------------------------------------------------------------------- #


def build_daily_series(
    loads: Iterable[DailyLoad],
    today: date,
    days: int = HISTORY_DAYS,
) -> list[float]:
    """把稀疏的日负荷补齐成一段连续的每日序列（缺失日填 0）。

    返回的列表长度为 `days`，最后一项是 `today`。冲激响应与 EWMA 都依赖
    "等间隔"假设，所以这里必须先做对齐。
    """
    buckets = {item.day: float(item.load) for item in loads}
    start = today - timedelta(days=days - 1)
    return [buckets.get(start + timedelta(days=offset), 0.0) for offset in range(days)]


def weekly_totals(series: Sequence[float], weeks: int = MONOTONY_WEEKS) -> list[float]:
    """把每日序列按 7 天一段从尾部切开，返回各周总负荷（按时间正序）。"""
    if not series:
        return []
    chunks: list[float] = []
    for start in range(len(series) - 7 * weeks, len(series), 7):
        end = min(start + 7, len(series))
        if end <= start:
            continue
        chunks.append(sum(series[start:end]))
    return chunks[-weeks:]


# --------------------------------------------------------------------------- #
# 三大模型
# --------------------------------------------------------------------------- #


def banister_impulse(
    series: Sequence[float],
    fitness_tau: float = FITNESS_TAU,
    fatigue_tau: float = FATIGUE_TAU,
) -> tuple[float, float, float]:
    """Banister 冲激响应：`series[0]` 是最旧的一天，末位是今天。

    返回 `(fitness, fatigue, tsb)`，均为负荷单位。
    """
    fitness = 0.0
    fatigue = 0.0
    n = len(series)
    for index, load in enumerate(series):
        if load <= 0:
            continue
        age = n - 1 - index  # 距今多少天
        fitness += load * math.exp(-age / fitness_tau)
        fatigue += load * math.exp(-age / fatigue_tau)
    return fitness, fatigue, fitness - fatigue


def acute_chronic_ratio(
    series: Sequence[float],
    acute_span: int = ACUTE_SPAN,
    chronic_span: int = CHRONIC_SPAN,
) -> tuple[float, float, float]:
    """EWMA 版 ACWR。返回 `(acute, chronic, ratio)`。

    慢性负荷为 0（新用户）时 ratio 取 1.0 —— 视为"既不超载也不欠载"。
    """
    acute = ewma(series, acute_span)
    chronic = ewma(series, chronic_span)
    if chronic <= 1e-6:
        return acute, chronic, 1.0
    return acute, chronic, acute / chronic


def monotony_strain(series: Sequence[float], weeks: int = MONOTONY_WEEKS) -> tuple[float, float]:
    """Foster 单调性与紧张度。返回 `(monotony, strain)`。"""
    totals = weekly_totals(series, weeks)
    if not totals:
        return 0.0, 0.0
    sd = standard_deviation(totals)
    if sd <= 1e-6:
        # 完全恒定的周负荷：单调性极高，用一个有限的替代值避免除零。
        return MONOTONY_ALERT + 1.0, sum(totals[-1:]) * (MONOTONY_ALERT + 1.0)
    monotony = (sum(totals) / len(totals)) / sd
    strain = totals[-1] * monotony
    return monotony, strain


def form_trend(scores: Sequence[float], window: int = TREND_WINDOW) -> float:
    """最近若干次会话的动作质量趋势（分/次）。正值代表在进步。"""
    recent = [float(s) for s in scores if s is not None][-window:]
    return linear_trend(recent)


# --------------------------------------------------------------------------- #
# 汇总
# --------------------------------------------------------------------------- #


def rest_gap(last_training_day: date | None, today: date) -> int:
    """距上次训练过去了几天。从未训练时返回一个很大的哨兵值。"""
    if last_training_day is None:
        return 999
    return max(0, (today - last_training_day).days)


def readiness_report(
    loads: Iterable[DailyLoad],
    today: date,
    days: int = HISTORY_DAYS,
) -> ReadinessReport:
    """把日负荷序列折算成一份可解释的准备度报告。"""
    items = sorted((item for item in loads if item.load > 0), key=lambda x: x.day)
    series = build_daily_series(items, today, days)

    acute, chronic, acwr = acute_chronic_ratio(series)
    fitness, fatigue, tsb = banister_impulse(series)
    trend = form_trend([item.form_score for item in items if item.form_score])
    weekly = weekly_totals(series)

    # 完全没有任何训练时，全零序列的"标准差为 0"会被误读成极端单调，这里直接短路。
    if not items or sum(series) <= 0:
        monotony, strain, weekly = 0.0, 0.0, []
    else:
        monotony, strain = monotony_strain(series)

    last_day = items[-1].day if items else None
    gap = rest_gap(last_day, today)

    # ---------- 打分 ----------
    score = 70.0
    reasons: list[str] = []

    # 1) TSB：体能减疲劳，用慢性负荷做归一化后映射到 ±14 分
    scale = chronic if chronic > 1e-6 else 1.0
    tsb_norm = _clamp(tsb / scale, -1.5, 1.5)
    score += tsb_norm * 9.0
    if tsb_norm > 0.35:
        reasons.append("体能储备高于疲劳，处于可以冲强度的状态")
    elif tsb_norm < -0.35:
        reasons.append("近期疲劳积累快于体能增长，需要控制总量")

    # 2) ACWR：甜蜜区不扣分，超出后线性惩罚。
    # 冷启动保护：慢性负荷基线还没建立时（新用户 / 长假归来），EWMA 比值天然
    # 会飙到 3+ 或掉到 0.2，此时按 `confidence` 打折，避免给出误导性的"超载"判定。
    confidence = _clamp(chronic / 20.0, 0.0, 1.0)
    if confidence < 0.5:
        # 基线太薄，比值本身没有解释力，只做轻微加权并如实说明。
        reasons.append("慢性负荷基线尚未建立，负荷比暂不作为主要依据")
    elif acwr > ACWR_DANGER:
        score -= min(22.0, (acwr - ACWR_DANGER) * 40.0) * confidence
        reasons.append(f"急性/慢性负荷比 {acwr:.2f} 超过 1.5，伤病风险偏高")
    elif acwr > ACWR_SWEET_HIGH:
        score -= (acwr - ACWR_SWEET_HIGH) * 12.0 * confidence
        reasons.append(f"负荷比 {acwr:.2f} 略高于甜蜜区，本周不要再叠加")
    elif acwr < ACWR_SWEET_LOW:
        score -= (ACWR_SWEET_LOW - acwr) * 25.0 * confidence
        reasons.append(f"负荷比 {acwr:.2f} 偏低，训练刺激不足")

    # 3) 单调性：长期一成不变的周负荷会抬高心理疲劳
    if monotony > MONOTONY_ALERT:
        score -= min(8.0, (monotony - MONOTONY_ALERT) * 5.0)
        reasons.append("训练安排过于单调，建议更换动作组合或调整强度分布")

    # 4) 恢复间隔：0 天说明今天已练过，1-2 天是典型的超量恢复窗口
    if gap == 0:
        score -= 6.0
        reasons.append("今天已经训练过，再练需要明显降低强度")
    elif gap == 1:
        score += 3.0
    elif gap == 2:
        score += 6.0
        reasons.append("距离上次训练 2 天，正处于超量恢复窗口")
    elif gap >= 5:
        score -= min(6.0, (gap - 4) * 1.5)
        reasons.append(f"已休息 {gap} 天，需要先做一次唤醒训练恢复节奏")

    # 5) 动作质量趋势
    score += _clamp(trend, -3.0, 3.0) * 3.0
    if trend >= 1.0:
        reasons.append("动作质量持续上升，可以适度加码")
    elif trend <= -1.5:
        reasons.append("动作质量下滑，优先做技术打磨而不是加重量")

    if not items:
        score = 68.0
        reasons.append("还没有历史训练数据，先按中等强度起步")
    elif len(items) < 5:
        # 样本太少时模型置信度低，向中性回归，避免给出极端建议
        score = 70.0 * 0.6 + score * 0.4
        reasons.append("历史样本较少，评分已向中性收敛")

    score = _clamp(score, MIN_SCORE, MAX_SCORE)

    # ---------- 分档与建议 ----------
    if score >= 80:
        tone, label, intensity = "excellent", "状态极佳", "hard"
        advice = "身体信号良好，可以安排一次高质量力量或技术训练。"
    elif score >= 62:
        tone, label, intensity = "good", "适合训练", "moderate"
        advice = "状态稳定，按计划完成中等强度训练即可。"
    elif score >= 45:
        tone, label, intensity = "moderate", "中等强度", "light"
        advice = "今天适合控制强度，把注意力放在动作质量上。"
    else:
        tone, label, intensity = "recover", "恢复优先", "rest"
        advice = "疲劳度偏高，建议安排低强度恢复训练并优先保证睡眠。"

    # ACWR 越界时强制降档，避免"高分但超载"的矛盾输出
    if acwr > ACWR_DANGER and intensity in {"hard", "moderate"}:
        intensity = "light"
        advice = "负荷增长过快，建议把今天改成低强度的有氧或拉伸。"

    multiplier = {
        "rest": 0.4,
        "light": 0.65,
        "moderate": 0.9,
        "hard": 1.1,
    }[intensity]
    if acwr > ACWR_SWEET_HIGH:
        multiplier *= 0.9

    components = ReadinessComponents(
        acute_load=acute,
        chronic_load=chronic,
        acwr=acwr,
        fitness=fitness,
        fatigue=fatigue,
        tsb=tsb,
        monotony=monotony,
        strain=strain,
        form_trend=trend,
        rest_days=gap if gap != 999 else -1,
        weekly_load=sum(series[-7:]) if series else 0.0,
        weekly_loads=weekly,
        session_count=len(items),
    )

    return ReadinessReport(
        score=int(round(score)),
        tone=tone,
        label=label,
        advice=advice,
        intensity=intensity,
        volume_multiplier=_clamp(multiplier, 0.35, 1.15),
        components=components,
        reasons=reasons,
    )


#: `UserTrainingSession.performance_score` 的满分（项目里是 0-5 分制）。
PERFORMANCE_SCALE = 5.0


#: 建议强度的中文标签，前端与训练计划共用同一份口径。
INTENSITY_LABELS = {
    "rest": "主动恢复",
    "light": "低强度",
    "moderate": "中等强度",
    "hard": "高强度",
}


def plan_volume(
    readiness: dict | None,
    base_sets: int = 3,
) -> tuple[int, float, str]:
    """把准备度报告折算成训练计划的容量。

    返回 `(每组组数, 容量系数, 强度中文标签)`。没有准备度（老接口 / 离线 / 取数失败）
    时原样返回 `base_sets` 与 1.0，保证计划一定能生成。
    """
    if not readiness:
        return base_sets, 1.0, "按计划"

    multiplier = _clamp(float(readiness.get("volume_multiplier") or 1.0), 0.4, 1.15)
    intensity = str(readiness.get("intensity") or "")
    return (
        max(2, min(5, int(round(base_sets * multiplier)))),
        multiplier,
        INTENSITY_LABELS.get(intensity, "按计划"),
    )


def load_curve(
    loads: Iterable[DailyLoad],
    today: date,
    days: int = 90,
    step: int = 1,
) -> list[dict]:
    """逐日（或按 `step` 抽样）回放体能 / 疲劳 / TSB 与 ACWR，供前端画曲线。

    每个采样点都用"截至当天"的负荷重新算一遍冲激响应，所以曲线反映的是
    当时真实的状态，而不是把最终结果摊平到每一天。
    """
    items = sorted((item for item in loads if item.load > 0), key=lambda x: x.day)
    buckets = {item.day: float(item.load) for item in items}

    window = max(HISTORY_DAYS, days + 1)
    points: list[dict] = []
    for offset in range(days - 1, -1, -step):
        day = today - timedelta(days=offset)
        start = day - timedelta(days=window - 1)
        series = [buckets.get(start + timedelta(days=i), 0.0) for i in range(window)]

        fitness, fatigue, tsb = banister_impulse(series)
        acute, chronic, acwr = acute_chronic_ratio(series)
        points.append(
            {
                "date": day.isoformat(),
                "fitness": round(fitness, 2),
                "fatigue": round(fatigue, 2),
                "tsb": round(tsb, 2),
                "acute_load": round(acute, 2),
                "chronic_load": round(chronic, 2),
                "acwr": round(acwr, 3),
            }
        )
    return points


def session_load(minutes: float, performance_score: float, scale: float = PERFORMANCE_SCALE) -> float:
    """把一次会话折算成训练负荷：`时长 × 强度系数`。

    表现分按 `scale` 归一化后映射到 0.7-1.25 的强度系数；缺失表现分（0）时按 1.0 计，
    避免把"未评分"误判成"极低强度"。单次负荷上限 180，防止超长会话把模型拉爆。
    """
    minutes = max(0.0, float(minutes or 0.0))
    score = float(performance_score or 0.0)
    if score <= 0:
        intensity = 1.0
    else:
        ratio = _clamp(score / scale, 0.0, 1.5)
        intensity = _clamp(0.6 + ratio * 0.4, 0.7, 1.25)
    return min(180.0, minutes * intensity)
