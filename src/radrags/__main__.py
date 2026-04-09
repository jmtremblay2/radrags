"""Launch the radrags query server: ``python -m radrags.server``."""

from __future__ import annotations

import argparse

import uvicorn

from radrags.server import create_app_from_config


def main() -> None:
    parser = argparse.ArgumentParser(description="radrags query server")
    parser.add_argument("--config", default=None, help="Path to INI config file")
    args = parser.parse_args()

    app = create_app_from_config(args.config)

    from radrags.config import load_config

    cfg = load_config(args.config)
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
