import torch
import os
from django.conf import settings
from exercises.models import Exercise
from .dl_models import ExerciseSequenceModel

class DLModelManager:
    _instance = None
    _model = None
    _id_to_idx = {}
    _idx_to_id = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DLModelManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # 1. 建立动作 ID 与 索引 的映射
        exercises = list(Exercise.objects.all().order_by('id'))
        self._id_to_idx = {ex.id: i + 1 for i, ex in enumerate(exercises)} # 从1开始，0预留给 padding
        self._idx_to_id = {i + 1: ex.id for i, ex in enumerate(exercises)}
        
        num_exercises = len(exercises)
        if num_exercises == 0:
            return

        # 2. 初始化模型
        self._model = ExerciseSequenceModel(num_exercises)
        
        # 3. 尝试加载权重
        model_path = os.path.join(settings.BASE_DIR, 'recommendations', 'weights', 'sequence_model.pth')
        if os.path.exists(model_path):
            try:
                self._model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
                print("✅ 深度学习推荐模型权重加载成功")
            except Exception as e:
                print(f"⚠️ 模型权重加载失败: {e}")
        else:
            print("ℹ️ 未找到预训练权重，使用随机初始化模型")
        
        self._model.eval()

    def predict(self, exercise_ids, limit=5):
        """
        给定动作 ID 序列，预测后续动作
        """
        if not self._model or not exercise_ids:
            return []

        # 转换为索引序列并 padding/截断
        indices = [self._id_to_idx.get(eid, 0) for eid in exercise_ids]
        input_tensor = torch.LongTensor([indices])
        
        with torch.no_grad():
            logits = self._model(input_tensor)
            # 排除掉输入序列中已有的动作（可选，视具体业务而定，但在组间推荐中通常推荐新动作）
            # logits[0, indices] = -float('inf') 
            
            probs = torch.softmax(logits, dim=1)
            top_probs, top_indices = torch.topk(probs, k=min(limit + 5, logits.size(1)))
            
        results = []
        for prob, idx in zip(top_probs[0], top_indices[0]):
            ex_id = self._idx_to_id.get(idx.item())
            if ex_id:
                results.append((ex_id, prob.item()))
        
        return results[:limit]

    def get_id_to_idx(self):
        return self._id_to_idx
