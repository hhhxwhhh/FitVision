from django.db import migrations

CHALLENGES = [
    {
        "code": "weekly_sessions",
        "title": "三次出击",
        "description": "本周完成 3 次训练",
        "period": "weekly",
        "metric": "sessions",
        "target": 3,
        "xp_reward": 60,
        "icon": "Calendar",
        "sort_order": 10,
    },
    {
        "code": "weekly_minutes",
        "title": "百二十分钟",
        "description": "本周累计训练 120 分钟",
        "period": "weekly",
        "metric": "minutes",
        "target": 120,
        "xp_reward": 60,
        "icon": "Clock",
        "sort_order": 20,
    },
    {
        "code": "weekly_volume",
        "title": "容量冲刺",
        "description": "本周累计训练容量达到 5000",
        "period": "weekly",
        "metric": "volume",
        "target": 5000,
        "xp_reward": 80,
        "icon": "DataLine",
        "sort_order": 30,
    },
    {
        "code": "weekly_variety",
        "title": "全能选手",
        "description": "本周完成 6 种不同动作",
        "period": "weekly",
        "metric": "distinct_exercises",
        "target": 6,
        "xp_reward": 50,
        "icon": "Compass",
        "sort_order": 40,
    },
    {
        "code": "weekly_quality",
        "title": "精益求精",
        "description": "本周单个动作评分达到 90 分",
        "period": "weekly",
        "metric": "best_form_score",
        "target": 90,
        "xp_reward": 70,
        "icon": "Aim",
        "sort_order": 50,
    },
    {
        "code": "monthly_sessions",
        "title": "月度恒心",
        "description": "本月完成 12 次训练",
        "period": "monthly",
        "metric": "sessions",
        "target": 12,
        "xp_reward": 150,
        "icon": "Trophy",
        "sort_order": 60,
    },
    {
        "code": "monthly_calories",
        "title": "热量熔炉",
        "description": "本月累计消耗 3000 千卡",
        "period": "monthly",
        "metric": "calories",
        "target": 3000,
        "xp_reward": 120,
        "icon": "HotWater",
        "sort_order": 70,
    },
]

ACHIEVEMENT = {
    "code": "challenge_5",
    "title": "挑战者",
    "description": "累计完成 5 次限时挑战",
    "category": "special",
    "metric": "challenges_claimed",
    "threshold": 5,
    "xp_reward": 100,
    "icon": "Trophy",
    "sort_order": 170,
}


def seed_challenges(apps, schema_editor):
    Challenge = apps.get_model("growth", "Challenge")
    Achievement = apps.get_model("growth", "Achievement")
    for item in CHALLENGES:
        Challenge.objects.update_or_create(code=item["code"], defaults=item)
    Achievement.objects.update_or_create(
        code=ACHIEVEMENT["code"], defaults=ACHIEVEMENT
    )


def unseed_challenges(apps, schema_editor):
    Challenge = apps.get_model("growth", "Challenge")
    Achievement = apps.get_model("growth", "Achievement")
    Challenge.objects.filter(code__in=[item["code"] for item in CHALLENGES]).delete()
    Achievement.objects.filter(code=ACHIEVEMENT["code"]).delete()


class Migration(migrations.Migration):
    dependencies = [("growth", "0003_challenges")]

    operations = [
        migrations.RunPython(seed_challenges, reverse_code=unseed_challenges)
    ]
