"""Deck em http://127.0.0.1:8020 (para navegadores que não leem arquivos locais, como o Zen).

uv run python apresentacao/servir.py
"""

from pathlib import Path

import uvicorn
from starlette.applications import Starlette
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

PASTA = Path(__file__).parent
uvicorn.run(
    Starlette(routes=[Mount("/", StaticFiles(directory=PASTA, html=True))]),
    host="127.0.0.1", port=8020, log_level="warning",
)  # fmt: skip
