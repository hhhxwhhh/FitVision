import os
import logging
from typing import Any
from openai import AsyncOpenAI 

logger = logging.getLogger(__name__)

class ChinaVLMService:
    def __init__(self) -> None:
        self.api_key = os.getenv('CN_VLM_API_KEY')
        self.model = os.getenv('CN_VLM_MODEL', 'doubao-1.5-vision-pro-250328')
        base_url = os.getenv('CN_VLM_BASE_URL', 'https://openkey.cloud/v1')
        
        self.client = None
        if self.api_key:
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=base_url
            )

    async def async_analyze_pose(self, payload: dict[str, Any], mode: str = 'realtime') -> dict[str, Any]:
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

        image_url = image_base64.strip()
        if not image_url.startswith('data:image'):
            image_url = f'data:image/jpeg;base64,{image_url}'

        # 将 mode 传给 prompt 构建器，以便针对不同模式生成不同的话术
        prompt = self._build_prompt(exercise_type, landmarks, motion_metrics, mode)
        
        try:
            response = await self.client.chat.completions.create(
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
                                    "detail": "low" 
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=450,
                timeout=55.0 
            )

            message = response.choices[0].message.content
            
            result = {
                'advice': message.strip() if message else "分析完成，动作节奏非常稳定，请继续保持。",
                'provider': 'OpenKey-Doubao',
                'model': self.model,
            }

            # 配合你的 views.py 逻辑：如果是诊断模式，给出一个默认的目标肌肉列表去触发课程推荐
            if mode == 'diagnosis':
                # 实际开发中，你可以让 Prompt 要求 AI 输出具体的肌肉名称，这里先做个简单的映射兜底
                if exercise_type == 'pushup':
                    result['recommended_target_muscles'] = ['胸大肌', '肱三头肌']
                elif exercise_type == 'squat':
                    result['recommended_target_muscles'] = ['股四头肌', '臀大肌']
                else:
                    result['recommended_target_muscles'] = ['核心肌群']

            return result
            
        except Exception as e:
            logger.error(f"VLM Analysis Error: {str(e)}")
            raise

    # 顺手把 mode 参数加进来，区分实时和诊断的话术
    def _build_prompt(self, exercise_type: str, landmarks: list[Any], motion_metrics: dict[str, Any], mode: str) -> str:
        rep_progress = motion_metrics.get('rep_progress', 0)
        last_score = motion_metrics.get('last_score', 0)
        rep_count = motion_metrics.get('rep_count', 0)
        
        base_prompt = (
            f"请针对这张画面中的动作姿态进行分析并给出语音纠正建议。\n"
            f"- 训练科目: {exercise_type}\n"
            f"- 动作进度: {rep_progress}% (接近 100% 为动作顶点)\n"
            f"- 算法评分: {last_score}/100\n"
            f"- 累计计数: {rep_count}\n"
            f"- 数据特征: 已检测到 {len(landmarks)} 个姿态核心锚点\n\n"
        )

        if mode == 'diagnosis':
            return base_prompt + "输出准则：\n1. 详细分析当前动作存在的结构性风险；\n2. 给出针对性的康复或改善建议；\n3. 语气要像专业理疗师。"
        else:
            return base_prompt + "输出准则：\n1. 用一句话肯定表现；\n2. 给出 2 条最急需改进的具体动作细节；\n3. 给 1 条安全警告；\n4. 总字数压缩在 150 字以内，语气要果断、专业。"

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