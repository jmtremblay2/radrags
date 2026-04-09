"""Launch the radrags query server: ``python -m radrags``."""

from __future__ import annotations

import uvicorn

from radrags.server import _build_parser, create_app_from_config


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    app, cfg = create_app_from_config(
        args.config,
        collection=args.collection,
        db_path=args.db_path,
        ollama_host=args.ollama_host,
        host=args.host,
        port=args.port,
    )
    uvicorn.run(app, host=cfg.host, port=cfg.port)


if __name__ == "__main__":
    main()
