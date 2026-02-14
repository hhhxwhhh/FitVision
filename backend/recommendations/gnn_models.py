import torch
import torch.nn as nn
import torch.nn.functional as F

class GCNLayer(nn.Module):
    """
    简单图卷积层 (Simple GCN Layer)
    """
    def __init__(self, in_features, out_features):
        super(GCNLayer, self).__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, x, adj):
        # x: (num_nodes, in_features)
        # adj: (num_nodes, num_nodes) 归一化邻接矩阵
        out = torch.mm(adj, x)
        out = self.linear(out)
        return out

class KnowledgeGraphGNN(nn.Module):
    """
    知识图谱图神经网络：用于学习动作之间的结构化表征
    以及预测动作之间的“进化路径”分值
    """
    def __init__(self, num_nodes, feature_dim, embedding_dim=32):
        super(KnowledgeGraphGNN, self).__init__()
        self.num_nodes = num_nodes
        
        # 节点嵌入层
        self.node_embedding = nn.Embedding(num_nodes, feature_dim)
        
        # 两层 GCN
        self.gcn1 = GCNLayer(feature_dim, embedding_dim)
        self.gcn2 = GCNLayer(embedding_dim, embedding_dim)
        
        # 连接预测/相似度计算
        self.fc = nn.Sequential(
            nn.Linear(embedding_dim * 2, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )

    def forward(self, x_indices, adj):
        # x_indices: 节点索引
        # adj: 归一化邻接矩阵
        
        # 1. 初始节点特征 (可以使用 One-hot 或 预定义特征)
        x = self.node_embedding(x_indices)
        
        # 2. 图卷积传播
        h = F.relu(self.gcn1(x, adj))
        h = self.gcn2(h, adj)
        
        # 返回所有节点的嵌入
        return h

    def predict_link(self, node_a_emb, node_b_emb):
        """预测两个节点之间的关联强度"""
        combined = torch.cat([node_a_emb, node_b_emb], dim=-1)
        return self.fc(combined)
