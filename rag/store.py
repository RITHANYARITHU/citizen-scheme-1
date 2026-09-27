"""Offline retrieval with an optional Chroma-compatible persistent backend."""

from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Any

from config import get_settings
from database.db import initialize_database, list_schemes


def _tokens(text: str) -> list[str]:
    return [token.casefold() for token in re.findall(r"[A-Za-z0-9\u0B80-\u0BFF]+", text) if len(token) > 1]


def _document(scheme: dict[str, Any]) -> str:
    return "\n".join(
        [
            scheme["name"],
            scheme["name_ta"],
            scheme["department"],
            scheme["summary"],
            scheme["summary_ta"],
            scheme["benefit"],
            " ".join(scheme["tags"]),
            "Eligibility: " + str(scheme["eligibility"]),
            "Documents: " + ", ".join(scheme["documents"]),
        ]
    )


def _embedding(text: str, dimensions: int = 96) -> list[float]:
    vector = [0.0] * dimensions
    for token in _tokens(text):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        vector[index] += 1.0 if digest[4] & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


class LocalRAGStore:
    """Small dependency-free retriever using SQLite seed records and token overlap."""

    def __init__(self, database_path: Path | str | None = None) -> None:
        self.database_path = database_path

    def query(self, question: str, limit: int = 5) -> list[dict[str, Any]]:
        schemes = list_schemes(self.database_path)
        query_terms = set(_tokens(question))
        ranked: list[tuple[float, dict[str, Any]]] = []
        for scheme in schemes:
            words = _tokens(_document(scheme))
            word_set = set(words)
            overlap = len(query_terms & word_set)
            score = overlap / math.sqrt(max(len(word_set), 1))
            if score > 0:
                ranked.append((score, scheme))
        ranked.sort(key=lambda item: (-item[0], item[1]["name"]))
        if not ranked:
            ranked = [(0.0, scheme) for scheme in schemes]
        return [
            {"id": scheme["id"], "document": _document(scheme), "metadata": scheme, "score": score}
            for score, scheme in ranked[:limit]
        ]


class ChromaCompatibleStore:
    """Optional Chroma adapter; uses explicit local hash embeddings (no model download)."""

    def __init__(self, persist_directory: Path | str, database_path: Path | str | None = None) -> None:
        try:
            import chromadb
        except ImportError as exc:
            raise RuntimeError("RAG_BACKEND=chroma requires chromadb; install requirements.txt or use RAG_BACKEND=local.") from exc
        self._client = chromadb.PersistentClient(path=str(persist_directory))
        self._collection = self._client.get_or_create_collection("citizen-schemes")
        self._database_path = database_path

    def _sync(self) -> None:
        records = list_schemes(self._database_path)
        if not records:
            return
        self._collection.upsert(
            ids=[record["id"] for record in records],
            documents=[_document(record) for record in records],
            embeddings=[_embedding(_document(record)) for record in records],
            metadatas=[{"name": record["name"], "source_url": record["source_url"]} for record in records],
        )

    def query(self, question: str, limit: int = 5) -> list[dict[str, Any]]:
        self._sync()
        result = self._collection.query(
            query_embeddings=[_embedding(question)],
            n_results=max(1, limit),
            include=["documents", "metadatas", "distances"],
        )
        records_by_id = {record["id"]: record for record in list_schemes(self._database_path)}
        ids = result.get("ids", [[]])[0]
        docs = result.get("documents", [[]])[0]
        metadata = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        return [
            {
                "id": item_id,
                "document": doc or "",
                "metadata": records_by_id.get(item_id, meta or {}),
                "score": 1.0 - float(distance),
            }
            for item_id, doc, meta, distance in zip(ids, docs, metadata, distances)
        ]


def get_rag_store(database_path: Path | str | None = None) -> LocalRAGStore | ChromaCompatibleStore:
    settings = get_settings()
    initialize_database(database_path)
    if settings.rag_backend == "chroma":
        return ChromaCompatibleStore(settings.base_dir / ".chroma", database_path)
    if settings.rag_backend == "local":
        return LocalRAGStore(database_path)
    raise ValueError(f"Unsupported RAG_BACKEND={settings.rag_backend!r}; choose 'local' or 'chroma'.")
