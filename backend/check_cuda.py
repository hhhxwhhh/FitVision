import torch
import sys

def check_cuda():
    print("-" * 50)
    print(f"Python 版本: {sys.version}")
    print(f"PyTorch 版本: {torch.__version__}")
    
    # 1. 核心可用性检查
    cuda_available = torch.cuda.is_available()
    print(f"CUDA 是否可用: {cuda_available}")
    
    # 2. 原因诊断
    if not cuda_available:
        print("\n[诊断建议]")
        if sys.platform == 'win32':
            print("1. 请检查是否安装了 NVIDIA 显卡驱动。")
            print("2. 检查 PyTorch 安装版本是否支持 CUDA。")
            print("   正常支持 CUDA 的版本后缀通常带有 +cuXXX (如 2.1.0+cu121)。")
            print(f"   当前安装版本后缀: {torch.__version__}")
            if '+' not in torch.__version__ or 'cu' not in torch.__version__:
                print("   警告: 看起来你安装的是 CPU 版本的 PyTorch。")
        
        print("\n[尝试查看 CUDA 编译版本]")
        print(f"PyTorch 编译时的 CUDA 版本: {torch.version.cuda}")
    else:
        # 3. 详细硬件信息
        print(f"CUDA 版本 (torch.version.cuda): {torch.version.cuda}")
        print(f"可用的 GPU 数量: {torch.cuda.device_count()}")
        for i in range(torch.cuda.device_count()):
            print(f"GPU {i}: {torch.cuda.get_device_name(i)}")
            print(f"  - 计算能力: {torch.cuda.get_device_capability(i)}")
            print(f"  - 当前显存使用: {torch.cuda.memory_allocated(i) / 1024**2:.2f} MB")

        # 4. 算力测试
        print("\n[运行简单算力测试...]")
        try:
            x = torch.rand(1000, 1000).cuda()
            y = torch.rand(1000, 1000).cuda()
            z = torch.matmul(x, y)
            print("✅ 显卡矩阵运算测试成功！")
        except Exception as e:
            print(f"❌ 显卡运算失败: {e}")

    print("-" * 50)

if __name__ == "__main__":
    check_cuda()
