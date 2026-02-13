import os
import requests
import json
import time
from django.core.management.base import BaseCommand
from exercises.models import Exercise

class Command(BaseCommand):
    help = '使用 DeepSeek API 分析并建立动作之间的前置/进阶关系'

    def handle(self, *args, **options):
        api_key = os.getenv('DEEPSEEK_API_KEY')
        if not api_key:
            self.stdout.write(self.style.ERROR('请在 .env 中设置 DEEPSEEK_API_KEY'))
            return

        # 获取所有动作
        all_exercises = Exercise.objects.all()
        muscle_groups = {}
        for ex in all_exercises:
            muscle = ex.target_muscle
            if muscle not in muscle_groups:
                muscle_groups[muscle] = []
            muscle_groups[muscle].append(ex)

        url = "https://api.deepseek.com/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        self.stdout.write(self.style.SUCCESS(f'检测到 {len(muscle_groups)} 个目标肌群，开始按肌群分析关联关系...'))

        for muscle, exercises in muscle_groups.items():
            if len(exercises) < 2:
                continue
                
            muscle_name = exercises[0].get_target_muscle_display()
            self.stdout.write(f"\n正在分析肌群: {muscle_name} ({len(exercises)} 个动作)")
            
            exercise_list_str = "\n".join([f"- {ex.name} (难度等级:{ex.level}, 英文:{ex.english_name})" for ex in exercises])
            
            prompt = f"""
            你是一个健身专家。现在我有一个健身动作列表，这些动作都属于“{muscle_name}”肌群。
            你的任务是识别出这些动作之间的“前置关系（Prerequisite）”。
            
            规则：
            1. 如果动作A是动作B的基础/简单版本，或者在学习动作B之前应该先掌握动作A，那么 A 就是 B 的前置动作。
            2. 一个动作可以有0个或多个前置动作。
            3. 只有在这个列表中的动作才能互相关联。
            4. 进阶动作的 level 通常高于前置动作。
            
            待分析动作列表：
            {exercise_list_str}
            
            请返回JSON格式，结构如下：
            {{
                "relationships": [
                    {{"exercise": "进阶动作名称", "prerequisites": ["基础动作1", "基础动作2"]}},
                    ...
                ]
            }}
            只输出JSON，不要有任何多余文字。
            """

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": f"你是一个专业的健身教练助手，擅长分析{muscle_name}训练动作的递进关系。"},
                    {"role": "user", "content": prompt}
                ],
                "response_format": {"type": "json_object"}
            }

            try:
                response = requests.post(url, headers=headers, json=data, timeout=60)
                response.raise_for_status()
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                res_data = json.loads(content)
                relationships = res_data.get('relationships', [])
                
                for rel in relationships:
                    target_ex_name = rel.get('exercise')
                    pre_names = rel.get('prerequisites', [])
                    
                    target_ex = Exercise.objects.filter(name=target_ex_name).first()
                    if not target_ex:
                        continue
                        
                    for pre_name in pre_names:
                        pre_ex = Exercise.objects.filter(name=pre_name).first()
                        if pre_ex and pre_ex != target_ex:
                            target_ex.prerequisites.add(pre_ex)
                            self.stdout.write(self.style.SUCCESS(f"  关联成功: {pre_ex.name} -> {target_ex.name}"))
                
                # 稍微延迟一下防止触发速率限制
                time.sleep(1)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"分析该肌群时出错 {muscle_name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS('\n所有动作关联关系分析建立完成！'))
