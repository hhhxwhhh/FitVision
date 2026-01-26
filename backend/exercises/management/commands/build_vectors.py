from django.core.management.base import BaseCommand
from utils.vector_db import VectorDB

class Command(BaseCommand):
    help = '读取 SQL 数据库中的所有动作，并构建向量索引'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('正在启动向量库构建程序...'))
        
        try:
            # 初始化向量库工具
            db = VectorDB()
            # 执行重建
            db.rebuild_index()
            
            self.stdout.write(self.style.SUCCESS('向量库构建成功！'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'构建失败: {str(e)}'))