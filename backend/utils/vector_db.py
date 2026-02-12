import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from django.conf import settings
import os
import shutil

class VectorDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorDB, cls).__new__(cls)
            print("⏳ 正在初始化 M3E 中文向量模型...")
            
            persist_path = os.path.join(settings.BASE_DIR, 'chroma_db_data')
            model_name = "moka-ai/m3e-base"
            
            cls._instance.client = chromadb.PersistentClient(path=persist_path)
            
            cls._instance.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )

            # 🔥🔥🔥 修正后的逻辑 🔥🔥🔥
            try:
                # 1. 尝试获取现有集合
                cls._instance.collection = cls._instance.client.get_collection(
                    name="fitness_exercises",
                    embedding_function=cls._instance.ef
                )
            except Exception:
                # 2. 如果获取失败（不存在，或维度不匹配），准备重建
                print("⚠️ 检测到需要重建向量集合...")
                
                # 3. 尝试删除旧的（如果不存在就忽略错误，防止报错）
                try:
                    cls._instance.client.delete_collection("fitness_exercises")
                except Exception:
                    pass # 删不掉就算了，说明本来就没有

                # 4. 创建新的
                cls._instance.collection = cls._instance.client.create_collection(
                    name="fitness_exercises",
                    embedding_function=cls._instance.ef
                )
                
            print("✅ M3E 中文向量库初始化完成！")
        return cls._instance

    def rebuild_index(self):
        from exercises.models import Exercise
        print("🔄 开始基于 M3E 重建索引...")
        
        exercises = Exercise.objects.filter(is_active=True)
        if not exercises.exists():
            print("⚠️ 数据库为空，跳过。")
            return

        # 清空现有数据
        try:
            current_ids = self.collection.get()['ids']
            if current_ids:
                self.collection.delete(ids=current_ids)
        except:
            pass

        ids = []
        documents = []
        metadatas = []

        for ex in exercises:
            ids.append(str(ex.id))
            target_muscle_cn = ex.get_target_muscle_display()
            equipment_cn = ex.get_equipment_display()
            
            semantic_text = (
                f"动作：{ex.name}。\n"
                f"锻炼部位：{target_muscle_cn} {ex.target_muscle}。\n"
                f"器械：{equipment_cn}。\n"
                f"分类：{ex.category.name if ex.category else '通用'}。\n"
                f"描述：{ex.description}。\n"
                f"细节：{ex.instructions}"
            )
            
            documents.append(semantic_text)
            metadatas.append({
                "name": ex.name,
                "target_muscle": ex.target_muscle,
                "muscle_cn": target_muscle_cn
            })

        if ids:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
        
        print(f"🎉 成功将 {len(ids)} 个动作载入 M3E 向量库！")

    def search(self, query_text, top_k=10):
        count = self.collection.count()
        if count == 0: return []
        real_k = min(top_k, count)
        results = self.collection.query(query_texts=[query_text], n_results=real_k)
        if results['ids']: return results['ids'][0]
        return []