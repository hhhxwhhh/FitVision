import os
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
from django.core.management.base import BaseCommand
from django.conf import settings
from exercises.models import Exercise, ExerciseGraph
from recommendations.gnn_models import KnowledgeGraphGNN

class Command(BaseCommand):
    help = '训练知识图谱图神经网络模型并保存权重 (由后端补全生成)'

    def handle(self, *args, **options):
        self.stdout.write("正在准备训练 GNN 知识图谱模型...")
        
        # 1. 结构化图数据
        exercises = list(Exercise.objects.all().prefetch_related('prerequisites'))
        num_nodes = len(exercises)
        if num_nodes == 0:
            self.stdout.write(self.style.ERROR("未找到动作数据，无法训练。"))
            return
            
        ex_id_to_idx = {ex.id: i for i, ex in enumerate(exercises)}
        
        # 2. 构造邻接矩阵 (融合前置条件与用户路径权重)
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        adj = torch.eye(num_nodes).to(device)
        
        # 基础专家权重 (前置条件)
        for ex in exercises:
            for pre in ex.prerequisites.all():
                if pre.id in ex_id_to_idx:
                    # 前置关系是强关联
                    adj[ex_id_to_idx[pre.id], ex_id_to_idx[ex.id]] = 2.0
        
        # 用户行为权重 (ExerciseGraph)
        behavior_links = ExerciseGraph.objects.select_related('from_exercise', 'to_exercise')
        for link in behavior_links:
            if link.from_exercise_id in ex_id_to_idx and link.to_exercise_id in ex_id_to_idx:
                # 累加用户行为强度
                adj[ex_id_to_idx[link.from_exercise_id], ex_id_to_idx[link.to_exercise_id]] += (link.weight * 0.1)

        # 归一化 D^-1/2 * A * D^-1/2
        rowsum = adj.sum(1)
        d_inv_sqrt = torch.pow(rowsum, -0.5).flatten()
        d_inv_sqrt[torch.isinf(d_inv_sqrt)] = 0.
        d_mat_inv_sqrt = torch.diag(d_inv_sqrt)
        adj_norm = d_mat_inv_sqrt.mm(adj).mm(d_mat_inv_sqrt)
        
        # 3. 初始化模型和优化器
        # feature_dim 设为 16 (基于 level 和 类别等元数据的 Embedding)
        model = KnowledgeGraphGNN(num_nodes=num_nodes, feature_dim=16).to(device)
        optimizer = optim.Adam(model.parameters(), lr=0.01)
        
        # 自监督学习：训练模型使相邻节点嵌入尽可能相似 (Link Prediction Task)
        self.stdout.write("开始自监督训练 (50 轮)...")
        model.train()
        x_indices = torch.arange(num_nodes).to(device)
        
        for epoch in range(50):
            optimizer.zero_grad()
            embeddings = model(x_indices, adj_norm)
            
            # 计算对比损失：正样本（有边相连）嵌入距离应近，负样本应远
            # 此处演示通过邻接矩阵重构进行重构损失计算
            reconstruction = torch.mm(embeddings, embeddings.t())
            loss = F.mse_loss(reconstruction, adj_norm)
            
            loss.backward()
            optimizer.step()
            
            if epoch % 10 == 0:
                self.stdout.write(f"  Epoch {epoch}, Loss: {loss.item():.6f}")

        # 4. 保存模型权重
        weights_dir = os.path.join(settings.BASE_DIR, 'recommendations', 'weights')
        if not os.path.exists(weights_dir):
            os.makedirs(weights_dir)
            
        weights_path = os.path.join(weights_dir, 'gnn_model.pth')
        torch.save(model.state_dict(), weights_path)
        
        self.stdout.write(self.style.SUCCESS(f"模型训练完成。权重已保存至: {weights_path}"))
        self.stdout.write("现在推荐系统将使用训练好的 GNN 嵌入进行逻辑预测。")
