"""Tests for radrags.config — INI-based configuration loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

from radrags.config import ServerConfig, load_config


class TestLoadConfig:
    """Load an INI file and return a ServerConfig."""

    def test_loads_all_fields_from_ini(self, tmp_path: Path) -> None:
        ini = tmp_path / "test.ini"
        ini.write_text(textwrap.dedent("""\
                [radrags]
                db_path = /data/my_chroma
                collection = docs
                embedding_model = mxbai-embed-large
                ollama_host = http://10.0.0.1:11434
                host = 127.0.0.1
                port = 9000
            """))
        cfg = load_config(str(ini))
        assert cfg.db_path == "/data/my_chroma"
        assert cfg.collection == "docs"
        assert cfg.embedding_model == "mxbai-embed-large"
        assert cfg.ollama_host == "http://10.0.0.1:11434"
        assert cfg.host == "127.0.0.1"
        assert cfg.port == 9000

    def test_defaults_when_no_file(self) -> None:
        cfg = load_config(None)
        assert cfg.db_path == "./chroma_db"
        assert cfg.collection == "radrags"
        assert cfg.embedding_model == "nomic-embed-text"
        assert cfg.ollama_host == "http://127.0.0.1:11434"
        assert cfg.host == "0.0.0.0"
        assert cfg.port == 8000

    def test_defaults_for_missing_keys(self, tmp_path: Path) -> None:
        ini = tmp_path / "partial.ini"
        ini.write_text(textwrap.dedent("""\
                [radrags]
                collection = custom
            """))
        cfg = load_config(str(ini))
        assert cfg.collection == "custom"
        assert cfg.db_path == "./chroma_db"
        assert cfg.port == 8000
