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
