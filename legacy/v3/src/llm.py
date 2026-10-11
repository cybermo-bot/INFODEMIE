from __future__ import annotations

from typing import Any, Iterable, List

from langchain_ollama import ChatOllama
from ollama import Client

from .config import settings


def get_chat_model(temperature: float = 0.0) -> ChatOllama:
    return ChatOllama(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        temperature=temperature,
        num_ctx=8192,
    )


class OllamaEmbedder:
    def __init__(self, host: str | None = None, model: str | None = None) -> None:
        self.host = host or settings.ollama_base_url
        self.model = model or settings.embed_model
        self.client = Client(host=self.host)

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        payload = [str(text) for text in texts]
        if not payload:
            return []
        try:
            response = self.client.embed(model=self.model, input=payload)
            if isinstance(response, dict):
                return response.get("embeddings", [])
            return list(response.embeddings)
        except Exception:
            # Backward compatibility with older ollama python package versions.
            results: list[list[float]] = []
            for text in payload:
                old_response = self.client.embeddings(model=self.model, prompt=text)
                if isinstance(old_response, dict):
                    results.append(old_response.get("embedding", []))
                else:
                    results.append(list(old_response.embedding))
            return results

    def embed_query(self, text: str) -> list[float]:
        embeddings = self.embed_texts([text])
        return embeddings[0] if embeddings else []


def get_ollama_client() -> Client:
    return Client(host=settings.ollama_base_url)


def list_local_models() -> list[str]:
    client = get_ollama_client()
    try:
        response: Any = client.list()
    except Exception:
        return []
    if isinstance(response, dict):
        models = response.get("models", [])
    else:
        models = getattr(response, "models", [])
    output: list[str] = []
    for item in models:
        if isinstance(item, dict):
            output.append(item.get("model") or item.get("name") or "")
        else:
            output.append(getattr(item, "model", "") or getattr(item, "name", ""))
    return [name for name in output if name]


def ollama_status() -> dict[str, Any]:
    client = get_ollama_client()
    try:
        models = list_local_models()
        return {
            "ok": True,
            "base_url": settings.ollama_base_url,
            "models": models,
        }
    except Exception as exc:
        return {
            "ok": False,
            "base_url": settings.ollama_base_url,
            "error": str(exc),
            "models": [],
        }
