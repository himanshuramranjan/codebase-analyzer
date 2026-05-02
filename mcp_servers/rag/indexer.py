"""
mcp_servers/rag/indexer.py
Chunking and indexing logic.
Single responsibility: walk a repo, chunk files, upsert into ChromaDB.
"""
import sys
import hashlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from config import CHUNK_SIZE, CHUNK_OVERLAP, INDEXING_BATCH_SIZE, INDEXABLE_EXTENSIONS, SKIP_DIRS
from mcp_servers.rag.store import get_collection


def should_index(path: Path) -> bool:
    if path.suffix.lower() not in INDEXABLE_EXTENSIONS:
        return False
    for part in path.parts:
        if part in SKIP_DIRS or part.endswith(".egg-info"):
            return False
    return True


def chunk_file(file_path: Path, repo_root: Path) -> list[dict]:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []

    if not lines:
        return []

    rel_path = str(file_path.relative_to(repo_root))
    chunks = []
    step = CHUNK_SIZE - CHUNK_OVERLAP

    for start in range(0, len(lines), step):
        end = min(start + CHUNK_SIZE, len(lines))
        text = "\n".join(lines[start:end])
        if not text.strip():
            continue
        chunk_id = hashlib.md5(f"{rel_path}:{start}".encode()).hexdigest()
        chunks.append({
            "text": text,
            "id": chunk_id,
            "metadata": {
                "file": rel_path,
                "start_line": start,
                "end_line": end,
                "language": file_path.suffix.lstrip("."),
            },
        })
    return chunks


def index_repo(repo_path: Path) -> tuple[int, int]:
    """
    Walk repo_path, chunk every indexable file, upsert into ChromaDB.
    Returns (file_count, chunk_count).
    """
    collection = get_collection(create=True)

    all_files = [p for p in repo_path.rglob("*") if p.is_file() and should_index(p)]
    if not all_files:
        return 0, 0

    docs, metadatas, ids = [], [], []

    for file_path in all_files:
        for chunk in chunk_file(file_path, repo_path):
            docs.append(chunk["text"])
            metadatas.append(chunk["metadata"])
            ids.append(chunk["id"])

            if len(docs) >= INDEXING_BATCH_SIZE:
                collection.upsert(documents=docs, metadatas=metadatas, ids=ids)
                docs, metadatas, ids = [], [], []

    if docs:
        collection.upsert(documents=docs, metadatas=metadatas, ids=ids)

    return len(all_files), collection.count()