# app/core/__init__.py

from .embeddings import (
    initialize_embeddings,
    get_criminal_law_rag,
    get_precedent_index
)

__all__ = [
    "initialize_embeddings",
    "get_criminal_law_rag",
    "get_precedent_index"
]