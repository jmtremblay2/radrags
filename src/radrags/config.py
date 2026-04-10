"""INI-based configuration for the radrags server."""

from __future__ import annotations

import configparser
from dataclasses import dataclass


@dataclass
class ServerConfig:
    """Configuration values for the radrags query server."""

    db_path: str = "./chroma_db"
    collection: str = "radrags"
    embedding_model: str = "nomic-embed-text"
    ollama_host: str = "http://127.0.0.1:11434"
    host: str = "0.0.0.0"
    port: int = 8000


def load_config(path: str | None) -> ServerConfig:
    """Load server configuration from an INI file.

    Args:
        path: Path to an INI file. When ``None``, returns defaults.

    Returns:
        A populated ``ServerConfig`` instance.
    """
    if path is None:
        return ServerConfig()

    parser = configparser.ConfigParser()
    parser.read(path)

    section = "radrags"
    if not parser.has_section(section):
        return ServerConfig()

    get = parser[section].get
    defaults = ServerConfig()
    return ServerConfig(
        db_path=get("db_path", defaults.db_path),
        collection=get("collection", defaults.collection),
        embedding_model=get("embedding_model", defaults.embedding_model),
        ollama_host=get("ollama_host", defaults.ollama_host),
        host=get("host", defaults.host),
        port=int(get("port", str(defaults.port))),
    )


@dataclass
class AgentConfig:
    """Configuration values for the minimal agent."""

    ssh_host: str = "127.0.0.1"
    ssh_port: int = 22
    ssh_user: str = "vyos"
    ssh_key_path: str = "~/.ssh/id_ed25519"
    chat_model: str = "qwen3:32b"
    max_iterations: int = 10


def load_agent_config(path: str | None) -> AgentConfig:
    """Load agent configuration from an INI file.

    Args:
        path: Path to an INI file. When ``None``, returns defaults.

    Returns:
        A populated ``AgentConfig`` instance.
    """
    if path is None:
        return AgentConfig()

    parser = configparser.ConfigParser()
    parser.read(path)

    section = "agent"
    if not parser.has_section(section):
        return AgentConfig()

    get = parser[section].get
    defaults = AgentConfig()
    return AgentConfig(
        ssh_host=get("ssh_host", defaults.ssh_host),
        ssh_port=int(get("ssh_port", str(defaults.ssh_port))),
        ssh_user=get("ssh_user", defaults.ssh_user),
        ssh_key_path=get("ssh_key_path", defaults.ssh_key_path),
        chat_model=get("chat_model", defaults.chat_model),
        max_iterations=int(get("max_iterations", str(defaults.max_iterations))),
    )
