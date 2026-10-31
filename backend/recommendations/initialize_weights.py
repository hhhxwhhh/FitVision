import os
import sys
import django
import torch

# 设置 Django 环境
# 假设脚本在 backend/recommendations 目录下运行，将父目录添加到 sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fitvision.settings')
django.setup()

from exercises.models import Exercise
from recommendations.dl_models import ExerciseSequenceModel

def initialize_model():
    # 1. 统计 Exercise 数量
    num_exercises = Exercise.objects.count()
    print(f"Current number of exercises in database: {num_exercises}")
    
    # 如果数量为 0，设置一个默认值以防模型实例化失败或没有输出维度
    # 但根据要求，我们应使用实际数量
    if num_exercises == 0:
        print("Warning: No exercises found in database. Model will have 0 output dimensions.")

    # 2. 实例化模型
    # 使用默认参数，或者根据需要指定
    model = ExerciseSequenceModel(num_exercises=num_exercises)
    
    # 3. 确定保存路径
    weights_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'weights')
    if not os.path.exists(weights_dir):
        os.makedirs(weights_dir)
        
    model_path = os.path.join(weights_dir, 'sequence_model.pth')
    
    # 4. 保存模型状态字典
    torch.save(model.state_dict(), model_path)
    print(f"Model state dict saved to {model_path}")

if __name__ == "__main__":
    initialize_model()
