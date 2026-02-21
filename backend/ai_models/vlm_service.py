import os
import logging
import json
import time
from typing import Any, Optional
from openai import OpenAI, AsyncOpenAI

# 设置简单的日志记录
logger = logging.getLogger(__name__)

class ChinaVLMService:
    """
    针对 FitVision 优化的视觉语言模型 (VLM) 服务类。
    支持同步与异步调用，并强制结构化 JSON 输出。
    """
    _instance: Optional['ChinaVLMService'] = None

    def __new__(cls, *args, **kwargs) -> 'ChinaVLMService':
        if cls._instance is None:
            cls._instance = super(ChinaVLMService, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, '_initialized', False):
            return
            
        # 环境配置
        self.api_key = os.getenv('CN_VLM_API_KEY')
        self.model = os.getenv('CN_VLM_MODEL', 'doubao-1.5-vision-pro-250328')
        self.base_url = os.getenv('CN_VLM_BASE_URL', 'https://openkey.cloud/v1')
        
        # 初始化客户端（同步与异步）
        self.client = None
        self.async_client = None
        if self.api_key:
            try:
                self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
                self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI clients: {e}")
            
        self._initialized = True
        logger.info(f"VLM Service initialized with model: {self.model}")

    def _get_system_prompt(self, exercise_type: str, mode: str = 'realtime') -> str:
        """根据训练科目和分析模式生成系统提示词"""
        if mode == 'diagnosis':
            return (
                "你是一位专业的运动表现分析专家和人体工学专家。\n"
                "请针对上传的动作静态或动态截图进行深度姿态诊断。并返回严格的 JSON 格式。\n"
                "JSON 必须包含：\n"
                "1. 'score': 姿态健康度综合评分 0-100 (number)；\n"
                "2. 'summary': 核心结论 (string，限 15 字以内)；\n"
                "3. 'body_alignment': 人体力线分析，涵盖脊柱、双肩、盆骨、重心平衡度 (string)；\n"
                "4. 'risk_level': 风险等级 'low'/'medium'/'high' (string)；\n"
                "5. 'recommended_target_muscles': 需要加强的目标肌群，从 ['chest', 'back', 'shoulders', 'abs', 'legs', 'glutes'] 中选择 (array)；\n"
                "6. 'scenario_application': 该报告的应用场景建议，说明如何基于此报告调整后续训练逻辑 (string)；\n"
                "7. 'improvement_plan': 具体的未来两周改善动作路线建议 (string)。"
            )
        
        return (
            f"你是一位资深健身教练，擅长通过视觉分析{exercise_type}动作。\n"
            "请分析图片中的人体姿态，并返回严格的 JSON 格式。\n"
            "JSON 必须包含：\n"
            "1. 'advice': 针对当前帧的实时纠错建议 (string)；\n"
            "2. 'tts_alert': 3-8 字的极简指令，用于语音实时播报 (string)；\n"
            "3. 'score_vlm': 你对该动作标准度的评分 0-100 (number)；\n"
            "4. 'safety_risks': 潜在受伤风险描述，若无则为空 (string)；\n"
            "5. 'visual_focus': 你在图中观察到的关键异常点 (string)。"
        )

    def _prepare_image_url(self, image_base64: str) -> str:
        """规范化 Base64 图片格式"""
        image_url = image_base64.strip()
        if not image_url.startswith('data:image'):
            # 默认为 jpeg
            image_url = f'data:image/jpeg;base64,{image_url}'
        return image_url

    async def async_analyze_pose(self, payload: dict[str, Any], mode: str = 'realtime') -> dict[str, Any]:
        """异步接口：支持实时分析和深度诊断模式"""
        if not self.async_client:
            return self._get_fallback_response(payload, "API Client not configured")

        image_base64 = payload.get('image_base64', '')
        exercise_type = payload.get('exercise_type', 'general')
        landmarks = payload.get('landmarks', [])
        motion_metrics = payload.get('motion_metrics', {})

        image_url = self._prepare_image_url(image_base64)
        prompt = self._build_user_prompt(exercise_type, landmarks, motion_metrics, mode)
        start_time = time.time()

        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(exercise_type, mode)},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=800 if mode == 'diagnosis' else 400,
                response_format={"type": "json_object"},
                timeout=55.0
            )

            latency = (time.time() - start_time) * 1000
            content = response.choices[0].message.content
            
            try:
                result = json.loads(content) if content else {}
            except json.JSONDecodeError:
                result = {"advice": content, "tts_alert": "请注意修正动作"}

            result.update({
                'model': self.model,
                'latency_ms': round(latency, 2),
                'usage': {
                    'total_tokens': response.usage.total_tokens
                }
            })
            return result

        except Exception as e:
            logger.error(f"VLM Async Error: {str(e)}")
            return self._get_fallback_response(payload, str(e))

    def analyze_pose(self, payload: dict[str, Any]) -> dict[str, Any]:
        """同步接口：保持现有项目逻辑兼容"""
        if not self.client:
            return self._get_fallback_response(payload, "No Client")

        image_base64 = payload.get('image_base64', '')
        exercise_type = payload.get('exercise_type', 'general')
        image_url = self._prepare_image_url(image_base64)
        prompt = self._build_user_prompt(exercise_type, payload.get('landmarks', []), payload.get('motion_metrics', {}))
        
        start_time = time.time()
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt(exercise_type)},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url, "detail": "low"}}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=600,
                response_format={"type": "json_object"},
                timeout=55.0
            )
            
            latency_ms = (time.time() - start_time) * 1000
            content = response.choices[0].message.content
            
            try:
                result = json.loads(content) if content else {}
            except json.JSONDecodeError:
                result = {"advice": content, "tts_alert": "请注意修正动作"}
                
            result['latency_ms'] = round(latency_ms, 2)
            result['model'] = self.model
            return result
        except Exception as e:
            logger.error(f"VLM Sync Error: {str(e)}")
            return self._get_fallback_response(payload, str(e))

    def _build_user_prompt(self, exercise_type: str, landmarks: list[Any], metrics: dict[str, Any], mode: str = 'realtime') -> str:
        rep_progress = metrics.get('rep_progress', 0)
        last_score = metrics.get('last_score', 0)
        
        if mode == 'diagnosis':
            return (
                f"你正在进行一场专业的运动体态诊断。训练科目: {exercise_type}。\n"
                "请根据图片（包含关键点数据和画面表现）进行深度剖析。\n"
                "- 特别关注肩膀是否等高、骨盆是否倾斜、关节是否处在不安全位置。\n"
                "- 给出的报告必须具有医学和体育科学的严谨性。\n"
                "- 指明该用户接下来的提升方案和动作改进逻辑。\n"
                "- 描述如何将该报告结果应用于后续的自动化训练计划生成中。"
            )

        return (
            f"你是 FitVision AI 健身系统的核心视觉诊断引擎。请实时分析当前这一帧图像：\n"
            f"1. 训练科目: {exercise_type}\n"
            f"2. 当前动作阶段: {rep_progress}% (接近 100% 表示接近顶点)\n"
            f"3. MediaPipe 预判分数: {last_score}/100 (分数较低可能意味着姿态异常)\n\n"
            "诊断指令：\n"
            "- 如果发现身体倾斜、关节位置不对称或过载迹象，请给出具体的矫正建议。\n"
            "- 'tts_alert' 字段必须极短，以便于语音实时播报（如：'背部挺直'、'臀部下压'）。\n"
            "- 确保 JSON 格式合法且精简。"
        )

    def _get_fallback_response(self, payload: dict[str, Any], error_msg: str) -> dict[str, Any]:
        exercise_type = payload.get('exercise_type', 'general')
        metrics = payload.get('motion_metrics', {})
        return {
            'advice': self._fallback_advice(exercise_type, metrics),
            'tts_alert': "请继续保持专注",
            'score_vlm': metrics.get('last_score', 50),
            'safety_risks': "",
            'visual_focus': "本地分析模式",
            'provider': 'fallback',
            'error': error_msg
        }

    def _fallback_advice(self, exercise_type: str, metrics: dict[str, Any]) -> str:
        score = int(metrics.get('last_score', 0))
        if exercise_type == 'squat':
            return '下蹲时膝盖不要内扣，核心收紧。' if score < 70 else '深蹲幅度很好，注意节奏。'
        if exercise_type == 'pushup':
            return '俯卧撑身体尽量成直线，避免塌腰。'
        return '动作节奏良好，保持平稳呼吸。'
