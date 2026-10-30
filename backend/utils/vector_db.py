"""Lazy-initialised Chroma vector store for exercise semantic search.

Heavy ML dependencies (chromadb / sentence-transformers) are imported on first
use so that the Django project can start (and tests can run) without them.
"""

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)


class VectorDB:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            # Imported here on purpose: keeps `manage.py` startup light and lets
            # the rest of the project run when optional ML deps are missing.
            try:
                import chromadb
                from chromadb.utils import embedding_functions
            except ImportError as exc:  # pragma: no cover - depends on env
                raise RuntimeError(
                    "Vector search requires the optional ML dependencies. "
                    "Install them with `pip install -r requirements.txt`."
                ) from exc

            logger.info("Initialising M3E Chinese embedding model…")
            instance = super().__new__(cls)

            persist_path = os.path.join(settings.BASE_DIR, "chroma_db_data")
            model_name = os.getenv("EMBEDDING_MODEL", "moka-ai/m3e-base")

            instance.client = chromadb.PersistentClient(path=persist_path)
            instance.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=model_name
            )

            try:
                instance.collection = instance.client.get_collection(
                    name="fitness_exercises", embedding_function=instance.ef
                )
            except Exception:
                logger.warning("Vector collection missing or incompatible; rebuilding.")
                try:
                    instance.client.delete_collection("fitness_exercises")
                except Exception:
                    pass
                instance.collection = instance.client.create_collection(
                    name="fitness_exercises", embedding_function=instance.ef
                )

            logger.info("Vector store ready.")
            cls._instance = instance
        return cls._instance

    def rebuild_index(self):
        from exercises.models import Exercise

        logger.info("Rebuilding exercise vector index…")
        exercises = Exercise.objects.filter(is_active=True)
        if not exercises.exists():
            logger.warning("No active exercises; skipping index rebuild.")
            return

        try:
            current_ids = self.collection.get()["ids"]
            if current_ids:
                self.collection.delete(ids=current_ids)
        except Exception:
            logger.exception("Could not clear the existing vector collection.")

        ids, documents, metadatas = [], [], []
        for ex in exercises:
            ids.append(str(ex.id))
            target_muscle_cn = ex.get_target_muscle_display()
            equipment_cn = ex.get_equipment_display()
            documents.append(
                f"动作：{ex.name}。\n"
                f"锻炼部位：{target_muscle_cn} {ex.target_muscle}。\n"
                f"器械：{equipment_cn}。\n"
                f"分类：{ex.category.name if ex.category else '通用'}。\n"
                f"描述：{ex.description}。\n"
                f"细节：{ex.instructions}"
            )
            metadatas.append(
                {
                    "name": ex.name,
                    "target_muscle": ex.target_muscle,
                    "muscle_cn": target_muscle_cn,
                }
            )

        if ids:
            self.collection.add(documents=documents, metadatas=metadatas, ids=ids)
        logger.info("Indexed %s exercises.", len(ids))

    def search(self, query_text, top_k=10):
        count = self.collection.count()
        if count == 0:
            return []
        results = self.collection.query(query_texts=[query_text], n_results=min(top_k, count))
        if results["ids"]:
            return results["ids"][0]
        return []
