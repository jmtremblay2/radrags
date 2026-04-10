"""Quick smoke test: SSH to localhost and run a command."""

from radrags.ssh import VyOSClient

client = VyOSClient(
    host="localhost",
    port=22,
    user="jtremblay",
    key_path="~/.ssh/id_ed25519",
)

result = client.execute("ls -1 ~/ollama/radrags/src/radrags/")
print(f"exit code: {result.exit_code}")
print(f"stdout:\n{result.stdout}")
if result.stderr:
    print(f"stderr:\n{result.stderr}")

client.close()
