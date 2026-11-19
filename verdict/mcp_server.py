"""Local stdio MCP server for coding assistants."""
from mcp.server.fastmcp import FastMCP
from .engine import answer, debate

mcp = FastMCP("Verdict")


@mcp.tool()
def verdict_ask(question: str, allow_cloud: bool = False) -> str:
    """Answer a developer question. Cloud fallback is off unless explicitly requested."""
    return answer(question, "ask", allow_cloud)


@mcp.tool()
def verdict_explain(code_or_concept: str, allow_cloud: bool = False) -> str:
    """Explain supplied code or a technical concept."""
    return answer(code_or_concept, "explain", allow_cloud)


@mcp.tool()
def verdict_debug(error_or_logs: str, allow_cloud: bool = False) -> str:
    """Analyze supplied errors, logs, or failing behaviour."""
    return answer(error_or_logs, "debug", allow_cloud)


@mcp.tool()
def verdict_review(code: str, allow_cloud: bool = False) -> str:
    """Review supplied code for correctness, risks, and improvements."""
    return answer(code, "review", allow_cloud)


@mcp.tool()
def verdict_decide(question: str, allow_cloud: bool = False) -> str:
    """Run a three-stage optimist, critic, and judge decision analysis."""
    return debate(question, allow_cloud)


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
