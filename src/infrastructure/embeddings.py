from sentence_transformers import SentenceTransformer
from src.config import settings

_embedding_model = None

def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = SentenceTransformer(str(settings.EMBEDDING_MODEL_PATH))
    return _embedding_model