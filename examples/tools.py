"""Examples of each agent tool.

Prerequisites:
- Ollama running with nomic-embed-text
- ChromaDB indexed (see examples/vyos_index.py)
- SSH access (for show_config / run_command)

Each section can be run independently. Comment out what you don't have.
"""

from radrags.agent import query_docs, read_file_tool, run_command, show_config_tool
from radrags.ssh import SSHClient
from radrags.vectorstore import ChromaStore

# --- 1. query_docs ---
# Search indexed VyOS documentation for relevant chunks.
store = ChromaStore(db_path="./chroma_db", collection="vyos-1.4.3")
print(query_docs("how to generate wireguard keys", store=store))

# --- 2. read_file ---
# Read a local file so the agent can parse its contents.
print(read_file_tool(path="examples/tools.py"))

# --- 3. show_config ---
# Inspect router configuration over SSH.
# client = SSHClient(host="192.168.1.1", port=22, user="vyos", key_path="~/.ssh/id_ed25519")
# print(show_config_tool(client=client))
# print(show_config_tool(path="interfaces wireguard", client=client))

# --- 4. run_command ---
# Execute a command on the router. Requires human approval via approve_fn.
# def ask_user(cmd: str) -> bool:
#     return input(f"Run '{cmd}'? [y/N] ").strip().lower() == "y"
#
# print(run_command("show interfaces", client=client, approve_fn=ask_user))
# client.close()
