"""Agent tools and registry for the radrags minimal agent."""

from __future__ import annotations

from typing import Any, Callable


def query_docs(query: str, *, store: Any, top_k: int = 5) -> str:
    """Search the RAG vector store for documentation.

    Args:
        query: The search query.
        store: A ``ChromaStore`` instance.
        top_k: Number of results to return.

    Returns:
        Formatted string with chunk text and source files.
    """
    results = store.query(query, top_k=top_k)
    if not results:
        return "No results found."
    parts = []
    for i, r in enumerate(results, 1):
        source = r["metadata"].get("source_file", "unknown")
        parts.append(f"[{i}] (source: {source})\n{r['text']}")
    return "\n\n".join(parts)


def show_config_tool(*, path: str | None = None, client: Any) -> str:
    """Retrieve VyOS router configuration via SSH.

    Args:
        path: Optional configuration path filter
            (e.g. ``"interfaces wireguard"``).
        client: An ``SSHClient`` instance.

    Returns:
        The configuration output as a string.
    """
    cmd = "show configuration commands"
    if path:
        cmd = f"show configuration commands | grep '{path}'"
    result = client.execute(cmd)
    return result.stdout


def run_command(command: str, *, client: Any, approve_fn: Callable[[str], bool]) -> str:
    """Execute a command on the router with human approval.

    Args:
        command: The command to execute.
        client: An ``SSHClient`` instance.
        approve_fn: Callable that receives the command string and
            returns ``True`` to approve execution.

    Returns:
        Command stdout if approved, or a declined message.
    """
    if not approve_fn(command):
        return "Declined by user."
    result = client.execute(command)
    return result.stdout


def read_file_tool(*, path: str) -> str:
    """Read a local file and return its contents.

    Args:
        path: Path to the file to read.

    Returns:
        File contents, or an error message if not found.
    """
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        return f"File not found: {path}"


# ---------------------------------------------------------------------------
# Tool registry & schemas
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, Callable[..., str]] = {
    "query_docs": query_docs,
    "show_config": show_config_tool,
    "run_command": run_command,
    "read_file": read_file_tool,
}

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "query_docs",
            "description": "Search the VyOS documentation for relevant information.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query.",
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "show_config",
            "description": "Show the current VyOS router configuration. Optionally filter by path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Configuration path to filter (e.g. 'interfaces wireguard'). Omit for full config.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a command on the VyOS router. Requires human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The VyOS command to execute.",
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a local file (e.g. a WireGuard .conf file).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Path to the file to read.",
                    },
                },
                "required": ["path"],
            },
        },
    },
]
