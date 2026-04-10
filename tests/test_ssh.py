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
