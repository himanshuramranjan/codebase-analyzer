"""
config.py
Single source of truth for all constants and paths.
"""

from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
RAG_DIR = Path("./rag")
CHROMA_DB_PATH = RAG_DIR / "chroma_db"
EMBEDDING_MODEL_PATH = RAG_DIR / "embedding_model"
OUTPUT_DIR = Path("./output")

# ── ChromaDB ──────────────────────────────────────────────────────────────────
COLLECTION_NAME = "codebase"

# ── Indexing ──────────────────────────────────────────────────────────────────
CHUNK_SIZE = 40
CHUNK_OVERLAP = 10
MAX_FILES_LISTED = 200
MAX_SEARCH_OUTPUT_CHARS = 3000
INDEXING_BATCH_SIZE = 100

INDEXABLE_EXTENSIONS = {
    ".py", ".js", ".ts", ".java", ".kt", ".go", ".rs", ".cpp", ".c",
    ".h", ".cs", ".rb", ".swift", ".scala", ".md", ".txt",
    ".yaml", ".yml", ".toml", ".sh",
}

SKIP_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv",
    "venv", "env", "dist", "build",
}

# ── Groq ──────────────────────────────────────────────────────────────────────
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
AGENT_MODEL = "llama-3.3-70b-versatile"
CLASSIFIER_MODEL = "llama-3.1-8b-instant"
AGENT_MAX_TURNS = 15
CLASSIFIER_MAX_TOKENS = 10

# ── MCP ───────────────────────────────────────────────────────────────────────
ANALYZER_MCP_PARAMS = {
    "command": "python",
    "args": ["mcp_servers/server.py"],
}