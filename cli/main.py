import asyncio
import typer
from typing import List
from agent.analyzer_agent import run_agent

app = typer.Typer()

@app.command()
def ask(
    query: List[str] = typer.Argument(..., help="Your question about the codebase"),
    repo: str = typer.Option(..., "--repo", "-r", help="Absolute path to the repository to scan"),
):
    full_query = " ".join(query)
    result = asyncio.run(run_agent(full_query, repo_path=repo))

    print("\n--- Answer ---\n")
    print(result)

if __name__ == "__main__":
    app()