import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from django.conf import settings
import os

class VectorDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(VectorDB, cls).__new__(cls)
            print("⏳ 正在初始化向量模型...")

            persist_path = os.path.join(settings.BASE_DIR, 'chroma_db_data')

            cls._instance.client = chromadb.PersistentClient(path=persist_path)

            cls._instance.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name="all-MiniLM-L6-v2"
            )

            cls._instance.collection = cls._instance.client.get_or_create_collection(
                name="fitness_exercises",
                embedding_function=cls._instance.ef
            )
            print("✅ 向量数据库初始化完成！")
        return cls._instance

    def rebuild_index(self):
        """
        全量重建索引：从 SQL 数据库读取所有动作，写入向量库
        """
        from exercises.models import Exercise  

        print("🔄 开始重建动作向量库...")

        exercises = Exercise.objects.filter(is_active=True)
        if not exercises.exists():
            print("⚠️ 数据库中没有可用的动作，跳过重建。")
            return

        # 2. 准备数据
        ids = []
        documents = []
        metadatas = []

        for ex in exercises:
            ids.append(str(ex.id))

            target_muscle_cn = ex.get_target_muscle_display() 
            equipment_cn = ex.get_equipment_display()         
            difficulty_cn = ex.get_difficulty_display()    

            category_name = ex.category.name if ex.category else "未分类"

            semantic_text = (
                f"动作名称：{ex.name}。"
                f"针对部位：{target_muscle_cn}。"
                f"所需器材：{equipment_cn}。"
                f"动作分类：{category_name}。"
                f"难度：{difficulty_cn}。"
                f"动作描述：{ex.description}。"
                f"执行要领：{ex.instructions}"
            )
            
            documents.append(semantic_text)

            metadatas.append({
                "name": ex.name,
                "target_muscle": target_muscle_cn,
                "equipment": equipment_cn,
                "category": category_name
            })

        current_count = self.collection.count()
        if current_count > 0:
            all_ids = self.collection.get()['ids']
            if all_ids:
                self.collection.delete(ids=all_ids)

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        print(f"🎉 成功将 {len(ids)} 个动作载入向量库！")

    def search(self, query_text, top_k=5): 
        """
        语义搜索：返回 ID 和 距离
        """
        count = self.collection.count()
        if count == 0:
            return []
        
        real_k = min(top_k, count)

        results = self.collection.query(
            query_texts=[query_text],
            n_results=real_k
        )

        if results['ids']:
            return results['ids'][0]
        return []