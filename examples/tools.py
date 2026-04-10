"""Demo of each agent tool using mocks (no live services needed)."""

from unittest.mock import MagicMock

from radrags.agent import query_docs, read_file_tool, run_command, show_config_tool

# --- 1. query_docs: search the vector store ---
mock_store = MagicMock()
mock_store.query.return_value = [
    {
        "text": "Generate a keypair: `generate pki wireguard key-pair`",
        "metadata": {"source_file": "configuration/interfaces/wireguard.rst"},
        "distance": 0.12,
    },
]
print("=== query_docs ===")
print(query_docs("wireguard keys", store=mock_store))
print()

# --- 2. show_config: inspect router config via SSH ---
mock_client = MagicMock()
mock_client.execute.return_value = MagicMock(
    stdout="set interfaces wireguard wg0 address '10.10.0.1/24'\n"
    "set interfaces wireguard wg0 port '51820'\n",
    stderr="",
    exit_code=0,
)
print("=== show_config (filtered) ===")
print(show_config_tool(path="interfaces wireguard", client=mock_client))

# --- 3. run_command: human-in-the-loop approval ---
mock_client2 = MagicMock()
mock_client2.execute.return_value = MagicMock(
    stdout="[edit]\n", stderr="", exit_code=0
)
print("=== run_command (approved) ===")
print(run_command("configure", client=mock_client2, approve_fn=lambda cmd: True))

print("=== run_command (declined) ===")
print(run_command("configure", client=mock_client2, approve_fn=lambda cmd: False))
print()

# --- 4. read_file: read a local file ---
print("=== read_file (this script) ===")
content = read_file_tool(path=__file__)
print(f"First line: {content.splitlines()[0]}")
print()

print("=== read_file (missing) ===")
print(read_file_tool(path="/tmp/nonexistent.conf"))
