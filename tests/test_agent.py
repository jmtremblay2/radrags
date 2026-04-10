"""Tests for radrags.agent tools and registry."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from radrags.agent import (
    TOOL_REGISTRY,
    TOOL_SCHEMAS,
    query_docs,
    read_file_tool,
    run_command,
    show_config_tool,
)


class TestQueryDocs:
    """query_docs formats ChromaStore results for LLM context."""

    def test_returns_formatted_results(self) -> None:
        store = MagicMock()
        store.query.return_value = [
            {
                "text": "Generate a keypair with `generate pki wireguard`",
                "metadata": {"source_file": "configuration/interfaces/wireguard.rst"},
                "distance": 0.15,
            },
            {
                "text": "WireGuard is a simple VPN tunnel.",
                "metadata": {"source_file": "configuration/interfaces/wireguard.rst"},
                "distance": 0.30,
            },
        ]
        result = query_docs("wireguard keys", store=store)
        store.query.assert_called_once_with("wireguard keys", top_k=5)
        assert "generate pki wireguard" in result
        assert "wireguard.rst" in result

    def test_empty_results(self) -> None:
        store = MagicMock()
        store.query.return_value = []
        result = query_docs("nonexistent topic", store=store)
        assert "no results" in result.lower()


class TestShowConfigTool:
    """show_config_tool retrieves router config via SSH."""

    def test_full_config(self) -> None:
        client = MagicMock()
        client.execute.return_value = MagicMock(
            stdout="set interfaces ethernet eth0 address '10.0.0.1/24'\n",
            stderr="",
            exit_code=0,
        )
        result = show_config_tool(client=client)
        cmd = client.execute.call_args[0][0]
        assert "show configuration commands" in cmd
        assert "10.0.0.1/24" in result

    def test_filtered_config(self) -> None:
        client = MagicMock()
        client.execute.return_value = MagicMock(
            stdout="set interfaces wireguard wg0 address '10.10.0.1/24'\n",
            stderr="",
            exit_code=0,
        )
        result = show_config_tool(path="interfaces wireguard", client=client)
        cmd = client.execute.call_args[0][0]
        assert "interfaces wireguard" in cmd
        assert "wg0" in result


class TestRunCommand:
    """run_command gates execution behind approve_fn."""

    def test_approved_command_executes(self) -> None:
        client = MagicMock()
        client.execute.return_value = MagicMock(
            stdout="commit ok\n", stderr="", exit_code=0
        )
        approve = MagicMock(return_value=True)
        result = run_command("configure", client=client, approve_fn=approve)
        approve.assert_called_once_with("configure")
        client.execute.assert_called_once_with("configure")
        assert "commit ok" in result

    def test_declined_command_not_executed(self) -> None:
        client = MagicMock()
        approve = MagicMock(return_value=False)
        result = run_command("configure", client=client, approve_fn=approve)
        approve.assert_called_once_with("configure")
        client.execute.assert_not_called()
        assert "declined" in result.lower()


class TestReadFileTool:
    """read_file_tool reads local files for the agent."""

    def test_reads_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "wg0.conf"
        f.write_text("[Interface]\nPrivateKey = abc123\n")
        result = read_file_tool(path=str(f))
        assert "PrivateKey" in result
        assert "abc123" in result

    def test_missing_file_returns_error(self) -> None:
        result = read_file_tool(path="/nonexistent/file.conf")
        assert "not found" in result.lower()


class TestToolRegistry:
    """TOOL_REGISTRY and TOOL_SCHEMAS are consistent."""

    def test_registry_has_all_tools(self) -> None:
        expected = {"query_docs", "show_config", "run_command", "read_file"}
        assert set(TOOL_REGISTRY.keys()) == expected

    def test_schemas_match_registry(self) -> None:
        schema_names = {s["function"]["name"] for s in TOOL_SCHEMAS}
        assert schema_names == set(TOOL_REGISTRY.keys())

    def test_schemas_have_required_fields(self) -> None:
        for schema in TOOL_SCHEMAS:
            assert schema["type"] == "function"
            func = schema["function"]
            assert "name" in func
            assert "description" in func
            assert "parameters" in func
            assert func["parameters"]["type"] == "object"
