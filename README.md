# 🔍 Codebase Analyzer

A local AI agent that answers questions about any codebase using exact keyword search, semantic vector search (RAG), and file inspection — powered by Groq and a custom MCP server over stdio.

Point it at any local folder and ask questions in plain English. The agent picks the right tool for your query automatically and gives grounded answers with file paths and line numbers — no hallucination, no guessing.

---

## Use Cases

| Query Type | Example | Tool Used |
|---|---|---|
| Exact symbol lookup | "Where is ATMState defined?" | ripgrep |
| Concept / flow | "How does the withdrawal flow work?" | ChromaDB semantic search |
| Architecture | "What are the main components and how do they interact?" | ChromaDB semantic search |
| File inspection | "What does IdleState.java contain?" | read_code_file |
| Save output | "Trace the card insertion path and save to a file" | semantic search + filesystem MCP |

---

## Architecture

```
cli/main.py
    └── agent/analyzer_agent.py         # orchestration + agent setup
            ├── agent/classifier.py     # LLM-based query routing (semantic vs exact)
            ├── agent/prompts.py        # all prompt strings in one place
            └── mcp_servers/server.py   # MCP tool definitions
                    └── rag/
                        ├── embeddings.py   # local sentence-transformer setup
                        ├── store.py        # ChromaDB client + collection access
                        └── indexer.py      # file chunking + upsert logic
```

**Two MCP servers run in parallel:**
- `mcp_servers/server.py` — codebase tools (search, index, read)
- `@modelcontextprotocol/server-filesystem` — writes answers to `./output/`

**Query routing flow:**
```
User query
    → classifier.py (llama-3.1-8b-instant, ~200ms, one word response)
        → "exact"    → search_code (ripgrep) → read_code_file
        → "semantic" → index_codebase → search_codebase_semantic → read_code_file
                                                        ↓
                                              write_file (if requested)
```

---

## Project Structure

```
mcp_swoftware_assistant/
├── .env                          # secrets — GROQ_API_KEY (never commit)
├── .env.example                  # template for new developers
├── config.py                     # all constants and paths
├── pytest.ini                    # test configuration
├── cli/
│   └── main.py                   # CLI entry point (typer)
├── agent/
│   ├── __init__.py
│   ├── analyzer_agent.py         # Agent setup + run_agent()
│   ├── classifier.py             # classify_query() + build_first_step()
│   └── prompts.py                # AGENT_INSTRUCTIONS, step templates, classifier prompt
├── mcp_servers/
│   ├── server.py                 # MCP tool definitions only (@mcp.tool)
│   └── rag/
│       ├── __init__.py
│       ├── embeddings.py         # SentenceTransformerEmbeddingFunction setup
│       ├── store.py              # ChromaDB PersistentClient + get_collection()
│       └── indexer.py            # should_index(), chunk_file(), index_repo()
├── rag/
│   ├── embedding_model/          # locally saved all-MiniLM-L6-v2 (~90MB)
│   └── chroma_db/                # persistent ChromaDB vector index
├── output/                       # agent writes answers here
```

---

## MCP Tools

| Tool | Description |
|---|---|
| `list_files(repo)` | Lists all indexable files in the repo |
| `search_code(query, repo)` | Exact / regex search via ripgrep |
| `read_code_file(path, start, end)` | Reads a file slice by line range |
| `index_codebase(repo)` | Chunks and indexes the repo into ChromaDB |
| `search_codebase_semantic(query)` | Concept-level vector search over the index |

---

## File Responsibilities

Each file has a single responsibility — nothing bleeds across boundaries.

| File | Responsibility |
|---|---|
| `config.py` | All constants and paths — single source of truth |
| `rag/embeddings.py` | Embedding function setup |
| `rag/store.py` | ChromaDB client and collection access |
| `rag/indexer.py` | File walking, chunking, upserting |
| `server.py` | MCP tool definitions only |
| `agent/prompts.py` | All prompt strings |
| `agent/classifier.py` | Query classification and step building |
| `agent/analyzer_agent.py` | Agent setup and `run_agent()` entry point |

---

## Prerequisites

- Python 3.11+
- [ripgrep](https://github.com/BurntSushi/ripgrep) — `brew install ripgrep`
- Node.js 18+ — for the filesystem MCP server
- A [Groq API key](https://console.groq.com) — free tier works fine

---

## Installation

**1. Clone the repo**
```bash
git clone https://github.com/your-username/mcp-codebase-analyzer.git
cd mcp-codebase-analyzer
```

**2. Create and activate a virtual environment**
```bash
python -m venv agents
source agents/bin/activate
```

**3. Install Python dependencies**
```bash
pip install openai-agents groq chromadb sentence-transformers python-dotenv typer
```

**4. Install the filesystem MCP server**
```bash
npm install -g @modelcontextprotocol/server-filesystem
```

**5. Set up environment variables**
```bash
cp .env.example .env
# Open .env and add your GROQ_API_KEY
```

`.env.example`:
```bash
GROQ_API_KEY=your_groq_api_key_here
RAG_DIR=./rag
OUTPUT_DIR=./output
```

**6. Download the embedding model once (~90MB, stored locally)**
```bash
python3 -c "
from sentence_transformers import SentenceTransformer
SentenceTransformer('all-MiniLM-L6-v2').save('./rag/embedding_model')
print('Model saved to ./rag/embedding_model')
"
```

**7. Create required empty `__init__.py` files**
```bash
touch mcp_servers/rag/__init__.py agent/__init__.py tests/__init__.py
```

---

## Usage

```bash
python -m cli.main ask --repo /path/to/your/project "Your question here"
```

### Examples

**Exact symbol lookup — uses ripgrep, fast:**
```bash
python -m cli.main ask --repo /path/to/atm/src "Where is ATMState defined?"
```

**Concept / flow — uses ChromaDB semantic search:**
```bash
python -m cli.main ask --repo /path/to/atm/src "How does the withdrawal flow work end to end?"
```

**Architecture overview:**
```bash
python -m cli.main ask --repo /path/to/atm/src "What are the main components and how do they interact?"
```

**Save answer to a file:**
```bash
python -m cli.main ask --repo /path/to/atm/src "Trace the card insertion path and save the output to a file"
# Answer saved to ./output/card_insertion_path.md
```

---

## How RAG Works

On the first semantic query the agent calls `index_codebase`, which:

1. Walks the repo and finds all indexable files (`.py`, `.java`, `.ts`, `.go` and more)
2. Splits each file into overlapping 40-line chunks with a 10-line overlap to preserve context at boundaries
3. Converts each chunk into a 384-dimensional embedding using `all-MiniLM-L6-v2` running locally
4. Upserts into a persistent ChromaDB collection using content-hash IDs — safe to re-run

On subsequent runs the index is already on disk so indexing is skipped automatically.

**Why line-based chunking instead of character-based?**
Code context is better preserved by lines. A 500-character split can cut a method in half. A 40-line split respects logical structure.

**Why ripgrep AND ChromaDB?**
They solve different problems. Ripgrep is fast and exact — ideal when you know the symbol name. ChromaDB finds semantically related code when you don't know what to search for. The LLM classifier routes each query to the right tool automatically using `llama-3.1-8b-instant` (~200ms, returns one word).

---

## Verify the Index

Run this after indexing to confirm ChromaDB has your codebase:

```bash
python3 - <<'EOF'
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

client = chromadb.PersistentClient(path="./rag/chroma_db")
ef = SentenceTransformerEmbeddingFunction(
    model_name="./rag/embedding_model",
    device="cpu",
    normalize_embeddings=True,
)
col = client.get_collection("codebase", embedding_function=ef)
print(f"Total chunks indexed: {col.count()}")

results = col.query(
    query_texts=["state machine"],
    n_results=3,
    include=["documents", "metadatas"],
)
for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
    print(f"\n📄 {meta['file']} (lines {meta['start_line']}–{meta['end_line']})")
    print(doc[:200])
EOF
```

If `Total chunks indexed` is `0`, re-run the agent with an explicit index request:
```bash
python -m cli.main ask --repo /path/to/repo "Index this codebase and confirm how many files were indexed"
```


---

## Models Used

| Model | Purpose | Why |
|---|---|---|
| `llama-3.3-70b-versatile` | Main agent | Best tool-calling reliability on Groq |
| `llama-3.1-8b-instant` | Query classifier | Fastest + cheapest, only needs one word back |
| `all-MiniLM-L6-v2` | Embeddings | Local, free, no API calls after first download |

---

## Limitations

- **Index is not auto-updated** — if you modify the codebase, ask the agent to re-index or results may be stale
- **Large repos** — repos with 10,000+ files may take 1–2 minutes to index on first run
- **Multi-file logic** — answers about logic that spans many files may be incomplete due to chunk size limits
- **Tool-calling reliability** — occasional `tool_use_failed` errors can occur on Groq with complex multi-step queries; retry the query if this happens

---

## .gitignore

```gitignore
.env
rag/chroma_db/
rag/embedding_model/
output/
__pycache__/
*.pyc
agents/
.pytest_cache/
```
