"""
mcp_servers/rag/embeddings.py
Embedding function — configured once, imported wherever needed.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from config import EMBEDDING_MODEL_PATH


def get_embedding_fn() -> SentenceTransformerEmbeddingFunction:
    """
    Local embedding function backed by a saved model directory.
    Points to a local path so sentence-transformers never calls HuggingFace.

    Download the model once with:
        python3 -c "
        from sentence_transformers import SentenceTransformer
        SentenceTransformer('all-MiniLM-L6-v2').save('./rag/embedding_model')
        "
    """
    return SentenceTransformerEmbeddingFunction(
        model_name=str(EMBEDDING_MODEL_PATH.resolve()),
        device="cpu",
        normalize_embeddings=True,
    )