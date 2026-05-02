import numpy as np
from sentence_transformers import SentenceTransformer, util
from rank_bm25 import BM25Okapi
from pymorphy3 import MorphAnalyzer

from src.config import settings


def lemmatize(morph, text: str) -> list[str]:
    return [morph.parse(word)[0].normal_form for word in text.split()]


def get_bm25_search_engine(morph, summaries):
    tokenized = [lemmatize(morph, doc) for doc in summaries]
    return BM25Okapi(tokenized)


def get_bm25_search_result(
    query: str, summaries: list[str], morph, bm25_threshold: float
) -> list[int]:
    """Возвращаем id релевантных записей в БД используя простой bm25 поиск"""
    bm25_engine = get_bm25_search_engine(morph, summaries)
    scores = bm25_engine.get_scores(lemmatize(morph, query))
    relevant_indexies = [
        i for i in np.argsort(scores)[::-1] if scores[i] >= bm25_threshold
    ]
    return relevant_indexies


def get_embeddings_search_result(
    query: str, embeddings: list[list[float]], embedding_model, emb_threshold: float
) -> list[int]:
    """Возвращаем id релевантных записей в БД используя эмбединги"""
    query_embedding = embedding_model.encode(query)
    corpus_embeddings = np.array(embeddings, dtype=np.float32)
    scores = util.cos_sim(query_embedding, corpus_embeddings)[0].numpy()
    relevant_indexies = [
        i for i in np.argsort(scores)[::-1] if scores[i] >= emb_threshold
    ]
    return relevant_indexies


def find_candidates(
    query: str,
    summaries: list[str],
    embeddings: list[list[float]],
    morph: MorphAnalyzer,
    embedding_model: SentenceTransformer,
    bm25_threshold: float = settings.BM25_THRESHOLD,
    emb_threshold: float = settings.EMBEDDING_THRESHOLD,
):
    bm25_relevant_indexies = get_bm25_search_result(
        query, summaries, morph, bm25_threshold
    )
    emb_relevant_indexies = get_embeddings_search_result(
        query, embeddings, embedding_model, emb_threshold
    )
    results = set(bm25_relevant_indexies) | set(emb_relevant_indexies)
    return results
