"""OpenEnv-compatible server entry point for the deployed FastAPI app."""

from __future__ import annotations

import argparse
import os

import uvicorn

from backend import app


def main(host: str = "0.0.0.0", port: int | None = None) -> None:
    resolved_port = port if port is not None else int(os.getenv("PORT", "7860"))
    uvicorn.run(app, host=host, port=resolved_port)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the VulnArena OpenEnv server.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "7860")))
    args = parser.parse_args()
    if args.host == "0.0.0.0" and args.port == int(os.getenv("PORT", "7860")):
        main()
    else:
        main(host=args.host, port=args.port)
