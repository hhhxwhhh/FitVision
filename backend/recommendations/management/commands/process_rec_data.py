import os
import json
import torch
import numpy as np
from django.core.management.base import BaseCommand
from django.conf import settings
from recommendations.models import UserInteraction
from exercises.models import Exercise
from utils.vector_db import VectorDB

class Command(BaseCommand):
    help = '处理推荐系统模型训练所需的数据'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('正在开始数据预处理...'))
        
        data_dir = os.path.join(settings.BASE_DIR, 'recommendations', 'data')
        os.makedirs(data_dir, exist_ok=True)

        # 1. 处理序列模型数据 (DL Sequence)
        self.stdout.write('1. 正在生成用户练习序列数据...')
        user_sequences = []
        users = UserInteraction.objects.values_list('user_id', flat=True).distinct()
        
        for user_id in users:
            # 获取用户完成的动作序列
            interactions = UserInteraction.objects.filter(
                user_id=user_id, 
                interaction_type='finish'
            ).order_by('timestamp').values_list('exercise_id', flat=True)
            
            if len(interactions) >= 2:
                user_sequences.append(list(interactions))
        
        with open(os.path.join(data_dir, 'sequences.json'), 'w') as f:
            json.dump(user_sequences, f)
        self.stdout.write(f'   - 已保存 {len(user_sequences)} 条用户轨迹序列')

        # 2. 处理图网络数据 (GNN)
        self.stdout.write('2. 正在提取图谱拓扑结构...')
        exercises = list(Exercise.objects.all().order_by('id'))
        ex_id_to_idx = {ex.id: i for i, ex in enumerate(exercises)}
        
        edge_index = []
        for ex in exercises:
            for pre in ex.prerequisites.all():
                if pre.id in ex_id_to_idx:
                    # 记录边：从前置到后续
                    edge_index.append([ex_id_to_idx[pre.id], ex_id_to_idx[ex.id]])
        
        graph_data = {
            'num_nodes': len(exercises),
            'edge_index': edge_index,
            'id_map': {str(idx): eid for eid, idx in ex_id_to_idx.items()}
        }
        
        with open(os.path.join(data_dir, 'kg_structure.json'), 'w') as f:
            json.dump(graph_data, f)
        self.stdout.write(f'   - 已提取 {len(edge_index)} 条知识图谱关联边')

        # 3. 刷新向量数据库索引 (Vector DB)
        self.stdout.write('3. 正在同步向量数据库索引...')
        try:
            vdb = VectorDB()
            for ex in exercises:
                query_text = f"动作：{ex.name}。部位：{ex.get_target_muscle_display()}。描述：{ex.description}"
                vdb.collection.upsert(
                    ids=[str(ex.id)],
                    documents=[query_text],
                    metadatas=[{"target_muscle": ex.target_muscle, "difficulty": ex.difficulty}]
                )
            self.stdout.write('   - 向量索引同步完成')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'   - 向量索引同步失败: {e}'))

        self.stdout.write(self.style.SUCCESS('✅ 数据预处理全部完成！'))
