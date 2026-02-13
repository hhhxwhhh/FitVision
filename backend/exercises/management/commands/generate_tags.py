import os
import requests
import json
from django.core.management.base import BaseCommand
from django.db.models import Q
from exercises.models import Exercise

class Command(BaseCommand):
    help = '使用 DeepSeek API 为没有标签的动作生成标签'

    def handle(self, *args, **options):
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            self.stdout.write(self.style.ERROR('请在 .env 中设置 DEEPSEEK_API_KEY'))
            return

        # 找出标签为空列表或为 None 的动作
        exercises = Exercise.objects.filter(Q(tags=[]) | Q(tags__isnull=True))
        if not exercises.exists():
            self.stdout.write(self.style.SUCCESS('所有动作已有标签。'))
            return

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        for exercise in exercises:
            self.stdout.write(f"正在为 '{exercise.name}' 生成标签...")
            
            prompt = f"""
            你是一个健身专家。请根据以下健身动作的信息，生成不超过5个关键词标签（tags）。
            标签应该是简短的关键词，如“增肌”、“减脂”、“核心训练”、“无需器械”、“胸肌”等。
            请直接返回JSON格式，格式如下：{{"tags": ["标签1", "标签2", ...]}}
            不要有任何解释文字。
            
            动作名称：{exercise.name}
            英文名称：{exercise.english_name}
            动作描述：{exercise.description}
            目标肌群：{exercise.get_target_muscle_display()}
            动作要领：{exercise.instructions}
            """

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是一个专门生成健身动作标签的助手，只输出合法JSON。"},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }

            try:
                # 实际调用时请确保网络畅通
                response = requests.post(url, headers=headers, json=data, timeout=30)
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                res_data = json.loads(content)
                tags = res_data.get('tags', [])
                
                if isinstance(tags, list):
                    exercise.tags = tags[:5]
                    exercise.save()
                    self.stdout.write(self.style.SUCCESS(f"已为 '{exercise.name}' 保存标签: {exercise.tags}"))
                else:
                    self.stdout.write(self.style.WARNING(f"AI返回格式异常: {content}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"生成失败 {exercise.name}: {str(e)}"))
