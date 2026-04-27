from sentence_transformers import SentenceTransformer
from src.config import settings

model = SentenceTransformer(settings.EMBEDDING_MODEL)
model.save(settings.EMBEDDING_MODEL_PATH)
print(f"Модель сохранена в {settings.EMBEDDING_MODEL_PATH}")