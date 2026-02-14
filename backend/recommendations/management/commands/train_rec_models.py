import os
import json
import torch
import torch.nn as nn
import torch.optim as optim
from django.core.management.base import BaseCommand
from django.conf import settings
from recommendations.gnn_models import KnowledgeGraphGNN
from recommendations.services import DLSequenceEngine

class Command(BaseCommand):
    help = '训练推荐系统中的所有深度学习模型 (Sequence & GNN)'

    def handle(self, *args, **options):
        # 自动检测 GPU
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.stdout.write(self.style.SUCCESS(f'正在使用设备: {self.device}'))
        self.stdout.write(self.style.SUCCESS('正在开始模型训练任务...'))
        
        data_dir = os.path.join(settings.BASE_DIR, 'recommendations', 'data')
        weights_dir = os.path.join(settings.BASE_DIR, 'recommendations', 'weights')
        os.makedirs(weights_dir, exist_ok=True)

        # 1. 训练序列模型 (DL Sequence / GRU)
        self._train_sequence_model(data_dir, weights_dir)

        # 2. 训练图神经网络 (GNN)
        self._train_gnn_model(data_dir, weights_dir)

        self.stdout.write(self.style.SUCCESS('✅ 所有模型训练完成并行持久化！'))

    def _train_sequence_model(self, data_dir, weights_dir):
        self.stdout.write('1. 正在训练序列预测模型 (Sequence Engine)...')
        seq_file = os.path.join(data_dir, 'sequences.json')
        if not os.path.exists(seq_file):
            self.stdout.write(self.style.WARNING('   - 未找到序列数据，跳过。'))
            return

        with open(seq_file, 'r') as f:
            sequences = json.load(f)

        if not sequences:
            self.stdout.write(self.style.WARNING('   - 序列数据为空，跳过。'))
            return

        # 获取全局动作总数 (假设 ID 包含范围)
        from exercises.models import Exercise
        from recommendations.dl_models import ExerciseSequenceModel
        num_exercises = Exercise.objects.count()
        
        # 初始化模型
        model = ExerciseSequenceModel(num_exercises).to(self.device)
        from recommendations.model_utils import DLModelManager
        id_to_idx = DLModelManager().get_id_to_idx()
        
        criterion = nn.CrossEntropyLoss()
        optimizer = optim.Adam(model.parameters(), lr=0.005)

        model.train()
        for epoch in range(10): # 简化训练轮数
            total_loss = 0
            for seq in sequences:
                if len(seq) < 2: continue
                # 转换 ID 为 Index
                indices = [id_to_idx.get(eid, 0) for eid in seq]
                # 输入 [seq_len], 转换为 [1, seq_len]
                input_tensor = torch.LongTensor(indices[:-1]).unsqueeze(0).to(self.device)
                target_tensor = torch.LongTensor([indices[-1]]).to(self.device) # 预测最后一个
                
                optimizer.zero_grad()
                output = model(input_tensor)
                loss = criterion(output, target_tensor)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()
            
            if epoch % 2 == 0:
                self.stdout.write(f'   - Epoch {epoch}, Loss: {total_loss:.4f}')

        torch.save(model.state_dict(), os.path.join(weights_dir, 'sequence_model.pth'))
        self.stdout.write('   - 序列模型已保存至 weights/sequence_model.pth')

    def _train_gnn_model(self, data_dir, weights_dir):
        self.stdout.write('2. 正在训练图推理模型 (GNN Reasoning)...')
        kg_file = os.path.join(data_dir, 'kg_structure.json')
        if not os.path.exists(kg_file):
            self.stdout.write(self.style.WARNING('   - 未找到图结构数据，跳过。'))
            return

        with open(kg_file, 'r') as f:
            kg_data = json.load(f)

        num_nodes = kg_data['num_nodes']
        if num_nodes == 0: return

        # 修正 edge_index 格式为 [2, E]
        edge_index = torch.LongTensor(kg_data['edge_index']).t().to(self.device)
        
        # 初始化模型
        # 注意：此处需匹配 KnowledgeGraphGNN 的 __init__ 参数
        # def __init__(self, num_nodes, feature_dim, embedding_dim=32)
        model = KnowledgeGraphGNN(num_nodes=num_nodes, feature_dim=16, embedding_dim=32).to(self.device)
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        
        # 构造节点全集索引和简单的单位矩阵作为特征 (或者可以使用预训练 embedding)
        x_indices = torch.arange(num_nodes).to(self.device)
        # 简单构造一个归一化邻接矩阵用于训练
        adj = torch.eye(num_nodes).to(self.device)
        for src_idx, dst_idx in kg_data['edge_index']:
            adj[src_idx, dst_idx] = 1.0

        # 目标：自监督学习，让有连接的节点 embedding 更接近 (简化版)
        model.train()
        for epoch in range(20):
            optimizer.zero_grad()
            # 调用 forward(x_indices, adj)
            embeddings = model(x_indices, adj)
            
            # 一个非常简单的 Loss: 最小化连接节点之间的距离
            src, dst = edge_index[0], edge_index[1]
            loss = torch.mean(torch.norm(embeddings[src] - embeddings[dst], p=2, dim=1))
            
            loss.backward()
            optimizer.step()
            
            if epoch % 5 == 0:
                self.stdout.write(f'   - Epoch {epoch}, KG Loss: {loss.item():.4f}')

        torch.save(model.state_dict(), os.path.join(weights_dir, 'gnn_model.pth'))
        self.stdout.write('   - GNN模型已保存至 weights/gnn_model.pth')
