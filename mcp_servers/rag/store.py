"""
mcp_servers/rag/store.py
ChromaDB client and collection access.
Single responsibility: get or create the collection, nothing else.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import chromadb        
from chromadb import Settings
from config import CHROMA_DB_PATH, COLLECTION_NAME
from mcp_servers.rag.embeddings import get_embedding_fn

_client = None


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        CHROMA_DB_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DB_PATH),
            settings=chromadb.Settings(anonymized_telemetry=False),
        )
    return _client


def get_collection(create: bool = False):
    """
    Return the ChromaDB collection.
    Returns None if the index does not exist and create=False.
    """
    client = get_client()

    if create:
        return client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_fn(),
            metadata={"hnsw:space": "cosine"},
        )

    try:
        return client.get_collection(
            name=COLLECTION_NAME,
            embedding_function=get_embedding_fn(),
        )
    except Exception:
        return None