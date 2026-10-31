from django.db import migrations

ACHIEVEMENTS = [
    {
        "code": "first_session",
        "title": "初次登场",
        "description": "完成第一次训练",
        "category": "milestone",
        "metric": "sessions",
        "threshold": 1,
        "xp_reward": 50,
        "icon": "Trophy",
        "sort_order": 10,
    },
    {
        "code": "sessions_10",
        "title": "十次修炼",
        "description": "累计完成 10 次训练",
        "category": "milestone",
        "metric": "sessions",
        "threshold": 10,
        "xp_reward": 100,
        "icon": "Medal",
        "sort_order": 20,
    },
    {
        "code": "sessions_50",
        "title": "训练常客",
        "description": "累计完成 50 次训练",
        "category": "milestone",
        "metric": "sessions",
        "threshold": 50,
        "xp_reward": 300,
        "icon": "Trophy",
        "sort_order": 30,
    },
    {
        "code": "streak_3",
        "title": "三日连击",
        "description": "连续训练 3 天",
        "category": "streak",
        "metric": "streak",
        "threshold": 3,
        "xp_reward": 80,
        "icon": "TrendCharts",
        "sort_order": 40,
    },
    {
        "code": "streak_7",
        "title": "七日不辍",
        "description": "连续训练 7 天",
        "category": "streak",
        "metric": "streak",
        "threshold": 7,
        "xp_reward": 200,
        "icon": "Medal",
        "sort_order": 50,
    },
    {
        "code": "streak_30",
        "title": "月度铁人",
        "description": "连续训练 30 天",
        "category": "streak",
        "metric": "streak",
        "threshold": 30,
        "xp_reward": 600,
        "icon": "Trophy",
        "sort_order": 60,
    },
    {
        "code": "minutes_600",
        "title": "十小时俱乐部",
        "description": "累计训练 600 分钟",
        "category": "volume",
        "metric": "minutes",
        "threshold": 600,
        "xp_reward": 150,
        "icon": "Clock",
        "sort_order": 70,
    },
    {
        "code": "calories_5000",
        "title": "能量熔炉",
        "description": "累计消耗 5000 千卡",
        "category": "volume",
        "metric": "calories",
        "threshold": 5000,
        "xp_reward": 200,
        "icon": "HotWater",
        "sort_order": 80,
    },
    {
        "code": "form_90",
        "title": "动作大师",
        "description": "单个动作评分达到 90 分",
        "category": "quality",
        "metric": "best_form_score",
        "threshold": 90,
        "xp_reward": 120,
        "icon": "Aim",
        "sort_order": 90,
    },
    {
        "code": "pr_5",
        "title": "纪录收割者",
        "description": "累计创造 5 项个人纪录",
        "category": "exploration",
        "metric": "personal_records",
        "threshold": 5,
        "xp_reward": 150,
        "icon": "Star",
        "sort_order": 100,
    },
    {
        "code": "volume_10000",
        "title": "容量怪物",
        "description": "累计训练容量达到 10000",
        "category": "volume",
        "metric": "total_volume",
        "threshold": 10000,
        "xp_reward": 200,
        "icon": "DataLine",
        "sort_order": 110,
    },
    {
        "code": "explorer_10",
        "title": "动作探索者",
        "description": "累计训练 10 种不同动作",
        "category": "exploration",
        "metric": "distinct_exercises",
        "threshold": 10,
        "xp_reward": 120,
        "icon": "Compass",
        "sort_order": 120,
    },
    {
        "code": "weekly_3",
        "title": "稳定节奏",
        "description": "单周训练达到 3 天",
        "category": "milestone",
        "metric": "weekly_days",
        "threshold": 3,
        "xp_reward": 60,
        "icon": "Calendar",
        "sort_order": 130,
    },
    {
        "code": "early_bird",
        "title": "晨练者",
        "description": "在早上 7 点前完成 5 次训练",
        "category": "special",
        "metric": "early_sessions",
        "threshold": 5,
        "xp_reward": 80,
        "icon": "Sunrise",
        "sort_order": 140,
    },
    {
        "code": "night_owl",
        "title": "夜行训练家",
        "description": "在晚上 10 点后完成 5 次训练",
        "category": "special",
        "metric": "night_sessions",
        "threshold": 5,
        "xp_reward": 80,
        "icon": "Moon",
        "sort_order": 150,
    },
    {
        "code": "level_5",
        "title": "渐入佳境",
        "description": "达到 5 级",
        "category": "milestone",
        "metric": "level",
        "threshold": 5,
        "xp_reward": 200,
        "icon": "Star",
        "sort_order": 160,
    },
]


def seed_achievements(apps, schema_editor):
    Achievement = apps.get_model("growth", "Achievement")
    for item in ACHIEVEMENTS:
        Achievement.objects.update_or_create(code=item["code"], defaults=item)


def unseed_achievements(apps, schema_editor):
    Achievement = apps.get_model("growth", "Achievement")
    Achievement.objects.filter(code__in=[item["code"] for item in ACHIEVEMENTS]).delete()


class Migration(migrations.Migration):
    dependencies = [("growth", "0001_initial")]

    operations = [
        migrations.RunPython(seed_achievements, reverse_code=unseed_achievements)
    ]
