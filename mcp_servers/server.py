"""
mcp_servers/server.py
"""

import sys
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import SKIP_DIRS, MAX_FILES_LISTED, MAX_SEARCH_OUTPUT_CHARS
from mcp_servers.rag.store import get_collection
from mcp_servers.rag.indexer import index_repo

mcp = FastMCP("analyzer-agent")


# ── Tool 1: list_files ────────────────────────────────────────────────────────

@mcp.tool()
def list_files(repo: str, extension: str = "") -> str:
    """List files in the repo filtered by optional extension e.g. '.py'. repo: absolute path to repository folder."""
    try:
        matches = []
        for root, dirs, files in os.walk(repo):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
            for file in files:
                if not extension or file.endswith(extension):
                    matches.append(os.path.join(root, file))
        return "\n".join(matches[:MAX_FILES_LISTED]) or "No files found."
    except Exception as e:
        return f"Error: {e}"


# ── Tool 2: search_code ───────────────────────────────────────────────────────

@mcp.tool()
def search_code(query: str, repo: str) -> str:
    """Search for a keyword or pattern in a local code repository using ripgrep. query: the search term. repo: absolute path to the repository folder."""
    try:
        result = subprocess.run(
            ["rg", "--with-filename", "--line-number", "--context", "2", "-i", query, repo],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout[:MAX_SEARCH_OUTPUT_CHARS] or "No matches found."
    except FileNotFoundError:
        return "Error: ripgrep (rg) not installed. Run: brew install ripgrep"
    except subprocess.TimeoutExpired:
        return "Error: search timed out. Use a more specific query."
    except Exception as e:
        return f"Error: {e}"


# ── Tool 3: read_code_file ────────────────────────────────────────────────────

@mcp.tool()
def read_code_file(path: str, start: int = 0, end: int = 200) -> str:
    """Read a slice of a source code file by line range. path: absolute file path. start: first line 0-indexed. end: last line exclusive."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        total = len(lines)
        header = f"[Lines {start}–{min(end, total)} of {total} in {path}]\n\n"
        return header + "".join(lines[start:end])
    except FileNotFoundError:
        return f"Error: file not found — {path}"
    except Exception as e:
        return f"Error: {e}"


# ── Tool 4: index_codebase ────────────────────────────────────────────────────

@mcp.tool()
def index_codebase(repo: str) -> str:
    """
    Index a local code repository into ChromaDB for semantic search.
    Call this once before using search_codebase_semantic, or when the codebase changes.
    Safe to re-run — uses upsert so nothing is duplicated.
    repo: absolute path to the repository folder to index.
    """
    repo_path = Path(repo).resolve()
    if not repo_path.exists():
        return f"Error: path does not exist — {repo}"

    file_count, chunk_count = index_repo(repo_path)

    if file_count == 0:
        return f"No indexable files found in {repo}."

    return (
        f"Done. Indexed {file_count} files into {chunk_count} chunks. "
        f"You can now call search_codebase_semantic to query the codebase."
    )


# ── Tool 5: search_codebase_semantic ─────────────────────────────────────────

@mcp.tool()
def search_codebase_semantic(query: str, n_results: int = 5) -> str:
    """
    Semantic search over the indexed codebase using ChromaDB vector embeddings.
    Use for concept-level queries where you do not know the exact symbol or class name.
    Good for: 'how does authentication work', 'what manages state transitions', 'explain the payment flow'.
    Requires index_codebase to have been called first.
    query: natural language description of what you are looking for.
    n_results: number of top chunks to return, default 5.
    """
    collection = get_collection(create=False)

    if collection is None:
        return "Semantic index not found. Call index_codebase(repo) first, then retry."

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, 10),
        include=["documents", "metadatas", "distances"],
    )

    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]

    if not docs:
        return "No relevant code found. Try rephrasing or re-index with index_codebase."

    output = []
    for doc, meta, dist in zip(docs, metas, distances):
        score = round(1 - dist, 3)
        ref = f"{meta['file']} (lines {meta['start_line']}–{meta['end_line']})"
        output.append(f"📄 {ref} | Score: {score}\n```{meta.get('language', '')}\n{doc}\n```")

    return "\n---\n\n".join(output)


if __name__ == "__main__":
    mcp.run(transport="stdio")