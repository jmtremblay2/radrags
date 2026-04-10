"""Tests for radrags.ssh and AgentConfig."""

from __future__ import annotations

import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

from radrags.config import AgentConfig, load_agent_config


class TestAgentConfig:
    """Load an INI file [agent] section into AgentConfig."""

    def test_loads_all_fields_from_ini(self, tmp_path: Path) -> None:
        ini = tmp_path / "agent.ini"
        ini.write_text(textwrap.dedent("""\
            [agent]
            ssh_host = 10.0.0.1
            ssh_port = 2222
            ssh_user = admin
            ssh_key_path = /home/me/.ssh/id_rsa
            chat_model = qwen3:14b
            max_iterations = 20
        """))
        cfg = load_agent_config(str(ini))
        assert cfg.ssh_host == "10.0.0.1"
        assert cfg.ssh_port == 2222
        assert cfg.ssh_user == "admin"
        assert cfg.ssh_key_path == "/home/me/.ssh/id_rsa"
        assert cfg.chat_model == "qwen3:14b"
        assert cfg.max_iterations == 20

    def test_defaults_when_no_file(self) -> None:
        cfg = load_agent_config(None)
        assert cfg.ssh_host == "127.0.0.1"
        assert cfg.ssh_port == 22
        assert cfg.ssh_user == "vyos"
        assert cfg.ssh_key_path == "~/.ssh/id_ed25519"
        assert cfg.chat_model == "qwen3:32b"
        assert cfg.max_iterations == 10

    def test_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        ini = tmp_path / "partial.ini"
        ini.write_text(textwrap.dedent("""\
            [agent]
            ssh_host = 192.168.1.1
        """))
        cfg = load_agent_config(str(ini))
        assert cfg.ssh_host == "192.168.1.1"
        assert cfg.ssh_port == 22
        assert cfg.chat_model == "qwen3:32b"


import pytest

from radrags.ssh import CommandResult, VyOSClient


class TestSSHExecute:
    """VyOSClient.execute() runs a command over SSH and returns CommandResult."""

    def test_execute_returns_command_result(self) -> None:
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b"hello\n"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_ssh.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        with patch("radrags.ssh.paramiko.SSHClient", return_value=mock_ssh):
            client = VyOSClient(
                host="10.0.0.1", port=22, user="vyos", key_path="/tmp/fake_key"
            )
            result = client.execute("echo hello")

        assert isinstance(result, CommandResult)
        assert result.stdout == "hello\n"
        assert result.stderr == ""
        assert result.exit_code == 0

    def test_execute_captures_stderr(self) -> None:
        mock_ssh = MagicMock()
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b"command not found\n"
        mock_ssh.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        with patch("radrags.ssh.paramiko.SSHClient", return_value=mock_ssh):
            client = VyOSClient(
                host="10.0.0.1", port=22, user="vyos", key_path="/tmp/fake_key"
            )
            result = client.execute("badcmd")

        assert result.exit_code == 1
        assert "command not found" in result.stderr


class TestShowConfig:
    """VyOSClient.show_config() wraps execute with VyOS show commands."""

    def test_show_config_full(self) -> None:
        mock_ssh = MagicMock()
        config_output = "set interfaces ethernet eth0 address '192.168.1.1/24'\n"
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = config_output.encode()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_ssh.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        with patch("radrags.ssh.paramiko.SSHClient", return_value=mock_ssh):
            client = VyOSClient(
                host="10.0.0.1", port=22, user="vyos", key_path="/tmp/fake_key"
            )
            result = client.show_config()

        assert config_output in result
        # Should have called the full show command
        cmd_called = mock_ssh.exec_command.call_args[0][0]
        assert "show configuration commands" in cmd_called

    def test_show_config_filtered(self) -> None:
        mock_ssh = MagicMock()
        config_output = "set interfaces wireguard wg0 address '10.0.0.1/24'\n"
        mock_stdout = MagicMock()
        mock_stdout.read.return_value = config_output.encode()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr = MagicMock()
        mock_stderr.read.return_value = b""
        mock_ssh.exec_command.return_value = (MagicMock(), mock_stdout, mock_stderr)

        with patch("radrags.ssh.paramiko.SSHClient", return_value=mock_ssh):
            client = VyOSClient(
                host="10.0.0.1", port=22, user="vyos", key_path="/tmp/fake_key"
            )
            result = client.show_config("interfaces wireguard")

        assert config_output in result
        cmd_called = mock_ssh.exec_command.call_args[0][0]
        assert "interfaces wireguard" in cmd_called


class TestConnectionErrors:
    """VyOSClient raises ConnectionError on SSH failures."""

    def test_unreachable_host_raises_connection_error(self) -> None:
        import paramiko

        mock_ssh = MagicMock()
        mock_ssh.connect.side_effect = paramiko.ssh_exception.NoValidConnectionsError(
            {("10.0.0.1", 22): OSError("Connection refused")}
        )

        with patch("radrags.ssh.paramiko.SSHClient", return_value=mock_ssh):
            with pytest.raises(ConnectionError, match="10.0.0.1"):
                VyOSClient(
                    host="10.0.0.1", port=22, user="vyos", key_path="/tmp/fake_key"
                )

    def test_auth_failure_raises_connection_error(self) -> None:
        import paramiko

        mock_ssh = MagicMock()
        mock_ssh.connect.side_effect = paramiko.AuthenticationException(
            "Authentication failed"
        )

        with patch("radrags.ssh.paramiko.SSHClient", return_value=mock_ssh):
            with pytest.raises(ConnectionError, match="Authentication"):
                VyOSClient(
                    host="10.0.0.1", port=22, user="vyos", key_path="/tmp/fake_key"
                )
