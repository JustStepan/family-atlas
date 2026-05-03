import asyncio

from rank_bm25 import BM25Okapi

from src.database.utils import get_summaries


summaries = asyncio.run(get_summaries())


corpus = ["текст заметки 1", "текст заметки 2"]
tokenized = [doc.split() for doc in corpus]
bm25 = BM25Okapi(tokenized)
scores = bm25.get_scores(query.split())
