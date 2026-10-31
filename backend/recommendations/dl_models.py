import torch
import torch.nn as nn

class ExerciseSequenceModel(nn.Module):
    """
    优化的序列推荐模型：GRU + Self-Attention
    """
    def __init__(self, num_exercises, embedding_dim=64, hidden_dim=128):
        super(ExerciseSequenceModel, self).__init__()
        self.embedding = nn.Embedding(num_exercises + 1, embedding_dim, padding_idx=0)
        self.gru = nn.GRU(embedding_dim, hidden_dim, batch_first=True, bidirectional=True)
        
        # 注意力机制
        self.attention = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1)
        )
        
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dim, num_exercises)
        )
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        # x: (batch_size, seq_len)
        embedded = self.dropout(self.embedding(x))
        
        # gru_out: (batch_size, seq_len, hidden_dim * 2)
        gru_out, _ = self.gru(embedded)
        
        # 计算注意力权重
        weights = torch.softmax(self.attention(gru_out), dim=1)
        
        # 加权求和得到上下文向量 (Context Vector)
        context = torch.sum(weights * gru_out, dim=1)
        
        logits = self.fc(context)
        return logits
