import asyncio

from sentence_transformers import SentenceTransformer, util
import numpy as np

from src.config import settings
from src.database.utils import get_summaries


session_ids, summaries = asyncio.run(get_summaries())
query = 'пет проект family-atlas'
embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_PATH)


def cosine_similarity(query: str, summaries: list[str], threshold: float = 0.7) -> list[float]:
    if summaries is None or not isinstance(summaries, list):
        raise ValueError("summaries должен быть непустым списком строк")
    query_embedding = embedding_model.encode(query)
    corpus_embeddings = embedding_model.encode(summaries)
    scores = util.cos_sim(query_embedding, corpus_embeddings)[0].numpy()
    relevant_indexies = [i for i in np.argsort(scores)[::-1] if scores[i] >= threshold]
    return [session_ids[i] for i in relevant_indexies]

# получаем нужные суммари
def get_results():
    results = cosine_similarity(query, summaries)
    print(results)
    for i in results:
        print(f'result № {i} = {summaries[i][:200]}')


if __name__ == "__main__":
    get_results()