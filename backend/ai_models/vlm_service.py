import os
import logging
from typing import Any
import requests
from openai import OpenAI  # 使用 OpenAI SDK 以提高稳定性

# 设置简单的日志记录，方便开发者在控制台看到具体报错
logger = logging.getLogger(__name__)

class ChinaVLMService:
    def __init__(self) -> None:
        # 默认使用 OpenKey 平台调用的豆包 (Doubao) 模型
        self.api_key = os.getenv('CN_VLM_API_KEY')
        # 更新为更通用的 1.5 Pro Vision 版本
        self.model = os.getenv('CN_VLM_MODEL', 'doubao-1.5-vision-pro-250328')
        # OpenKey 的 OpenAI 兼容模式基础 URL 应该到 /v1
        base_url = os.getenv('CN_VLM_BASE_URL', 'https://openkey.cloud/v1')
        
        # 初始化 OpenAI 客户端
        self.client = None
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=base_url
            )

    def analyze_pose(self, payload: dict[str, Any]) -> dict[str, Any]:
        image_base64 = payload.get('image_base64', '')
        exercise_type = payload.get('exercise_type', 'general')
        landmarks = payload.get('landmarks', [])
        motion_metrics = payload.get('motion_metrics', {})

        if not self.client:
            logger.warning("VLM API Key not found, using fallback advice.")
            return {
                'advice': self._fallback_advice(exercise_type, motion_metrics),
                'provider': 'fallback',
                'model': 'rule-engine',
            }

        # 处理图片 URL，确保不包含重复头，并整理格式
        image_url = image_base64.strip()
        if not image_url.startswith('data:image'):
            image_url = f'data:image/jpeg;base64,{image_url}'

        prompt = self._build_prompt(exercise_type, landmarks, motion_metrics)
        
        try:
            # 使用 SDK 调用聊天接口（包含视觉消息）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位拥有运动人体科学基础的精英健身教练。请对当前这一帧的训练姿态进行深度解析，给予用户具备指导价值的微型纠错建议。"
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "low"  # low 模式对姿态分析够用了，速度更快
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=450,
                timeout=55.0  # 为模型推理留足 55s，彻底避免 502/504
            )

            # 获取解析建议
            message = response.choices[0].message.content
            
            return {
                'advice': message.strip() if message else "分析完成，动作节奏非常稳定，请继续保持。",
                'provider': 'OpenKey-Doubao',
                'model': self.model,
            }
        except Exception as e:
            logger.error(f"VLM Analysis Error: {str(e)}")
            raise

    def _build_prompt(self, exercise_type: str, landmarks: list[Any], motion_metrics: dict[str, Any]) -> str:
        rep_progress = motion_metrics.get('rep_progress', 0)
        last_score = motion_metrics.get('last_score', 0)
        rep_count = motion_metrics.get('rep_count', 0)
        
        # 结构化 Prompt 引导，增加对 MediaPipe 关键点的语义说明
        return (
            f"请针对这张画面中的动作姿态进行分析并给出语音纠正建议。\n"
            f"- 训练科目: {exercise_type}\n"
            f"- 动作进度: {rep_progress}% (接近 100% 为动作顶点)\n"
            f"- 算法评分: {last_score}/100\n"
            f"- 累计计数: {rep_count}\n"
            f"- 数据特征: 已检测到 {len(landmarks)} 个姿态核心锚点\n\n"
            "输出准则：\n"
            "1. 用一句话肯定表现（如稳定性、幅度等）；\n"
            "2. 给出 2 条最急需改进的具体动作细节（针对画面中的姿势）；\n"
            "3. 给 1 条安全警告（防止受伤）；\n"
            "4. 总字数压缩在 150 字以内，语气要果断、专业。"
        )

    def _fallback_advice(self, exercise_type: str, motion_metrics: dict[str, Any]) -> str:
        score = int(motion_metrics.get('last_score', 0))
        if exercise_type == 'squat':
            if score < 70:
                return '深蹲时重心稍靠后，膝盖朝脚尖方向，下蹲到大腿接近平行再起身。'
            return '深蹲动作较稳定，继续保持核心收紧与膝盖轨迹一致。'
        if exercise_type == 'pushup':
            return '俯卧撑注意身体保持一条直线，下降时肘部约45度，避免塌腰。'
        if exercise_type == 'plank':
            return '平板支撑保持头肩髋踝一线，收紧腹部与臀部，避免抬臀或塌腰。'
        return '动作节奏良好，建议保持呼吸稳定并控制动作幅度。'
