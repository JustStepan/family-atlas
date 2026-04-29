from sentence_transformers import SentenceTransformer
from src.config import settings

embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH)