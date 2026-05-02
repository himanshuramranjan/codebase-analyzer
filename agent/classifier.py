"""
agent/classifier.py
Query classification — single responsibility: decide semantic vs exact search.
"""

from openai import AsyncOpenAI
from config import CLASSIFIER_MODEL, CLASSIFIER_MAX_TOKENS
from agent.prompts import CLASSIFIER_SYSTEM_PROMPT, SEMANTIC_STEPS, EXACT_STEPS


async def classify_query(query: str, groq_client: AsyncOpenAI) -> str:
    """
    Use a fast LLM call to classify the query as 'semantic' or 'exact'.
    Uses the smallest/cheapest model — classification only, no tools involved.
    Returns 'semantic' or 'exact'.
    """
    response = await groq_client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        max_tokens=CLASSIFIER_MAX_TOKENS,
        temperature=0,
        messages=[
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": query},
        ],
    )
    result = response.choices[0].message.content.strip().lower()
    return result if result in ("semantic", "exact") else "semantic"


async def build_first_step(query: str, repo_path: str, groq_client: AsyncOpenAI) -> str:
    """Classify the query and return the appropriate step-by-step instruction."""
    query_type = await classify_query(query, groq_client)

    if query_type == "semantic":
        return SEMANTIC_STEPS.format(repo_path=repo_path)
    else:
        return EXACT_STEPS.format(repo_path=repo_path)