import asyncio

import numpy as np
from rank_bm25 import BM25Okapi
import pymorphy3

from src.database.utils import get_summaries


morph = pymorphy3.MorphAnalyzer()
session_ids, summaries = asyncio.run(get_summaries())
query = 'пет проект family-atlas'


def lemmatize(text: str) -> list[str]:
    return [morph.parse(word)[0].normal_form for word in text.split()]


def get_bm25_search_engine(summaries):
    """doc[1] поскольку summaries - tuple(id, summary)"""
    tokenized = [lemmatize(doc) for doc in summaries]
    return BM25Okapi(tokenized)


async def get_search_result(query, summaries, threshold: float = 1.0):
    """Возвращаем id релевантных записей в БД"""
    bm25_engine = get_bm25_search_engine(summaries)
    scores = bm25_engine.get_scores(lemmatize(query))
    relevant_indexies = [i for i in np.argsort(scores)[::-1] if scores[i] >= threshold]
    return [session_ids[i] for i in relevant_indexies]

# получаем нужные суммари
async def get_results():
    results = await get_search_result(query, summaries)
    print(results)
    for i in results:
        print(f'result № {i} = {summaries[i][:100]}')


if __name__ == "__main__":
    asyncio.run(get_results())