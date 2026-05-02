"""
agent/analyzer_agent.py
Agent setup and entry point — only orchestration lives here.
"""

from dotenv import load_dotenv
from agents import Agent, Runner, trace, OpenAIChatCompletionsModel
from agents.mcp import MCPServerStdio
import os
from openai import AsyncOpenAI

from config import (
    GROQ_BASE_URL, AGENT_MODEL, AGENT_MAX_TURNS,
    OUTPUT_DIR, ANALYZER_MCP_PARAMS,
)
from agent.prompts import AGENT_INSTRUCTIONS
from agent.classifier import build_first_step

load_dotenv(override=True)

# ── Groq client ───────────────────────────────────────────────────────────────
groq_client = AsyncOpenAI(
    base_url=GROQ_BASE_URL,
    api_key=os.getenv("GROQ_API_KEY"),
)

groq_model = OpenAIChatCompletionsModel(
    model=AGENT_MODEL,
    openai_client=groq_client,
)

# ── MCP params ────────────────────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

files_params = {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", str(OUTPUT_DIR.resolve())],
}


# ── Entry point ───────────────────────────────────────────────────────────────
async def run_agent(query: str, repo_path: str):
    first_step = await build_first_step(query, repo_path, groq_client)

    async with (
        MCPServerStdio(params=ANALYZER_MCP_PARAMS, client_session_timeout_seconds=60) as workspace_server,
        MCPServerStdio(params=files_params, client_session_timeout_seconds=30) as files_server,
    ):
        agent = Agent(
            name="analyzer_agent",
            instructions=AGENT_INSTRUCTIONS,
            model=groq_model,
            mcp_servers=[workspace_server, files_server],
        )

        augmented_query = (
            f"Repository path: {repo_path}\n\n"
            f"User question: {query}\n\n"
            f"Follow these steps exactly:\n{first_step}"
        )

        with trace("analyzer_agent"):
            result = await Runner.run(
                agent,
                augmented_query,
                max_turns=AGENT_MAX_TURNS,
            )

        return result.final_output