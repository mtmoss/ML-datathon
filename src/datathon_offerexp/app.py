"""API de decisao (FastAPI). DIA 5: implementar o endpoint /decide."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="OfferExp - API de Decisao", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """Checagem simples de saude do servico."""
    return {"status": "ok"}
