"""Log auditavel de decisoes em arquivo JSONL (uma decisao por linha)."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from datathon_offerexp.contracts import DecisionRecord

DEFAULT_LOG = Path("reports/decision_log.jsonl")


def append_decision(record: DecisionRecord, path: Path = DEFAULT_LOG) -> None:
    """Acrescenta um registro de decisao ao arquivo de log."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(asdict(record), ensure_ascii=False) + "\n")
