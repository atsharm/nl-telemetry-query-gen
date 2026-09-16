"""Minimal client for a local Ollama server's generate API."""

import os
import time

import requests

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")


class OllamaClient:
    def __init__(self, host: str = OLLAMA_HOST):
        self.host = host.rstrip("/")

    def generate(self, model: str, prompt: str) -> tuple[str, float]:
        """Returns (response_text, latency_seconds)."""
        start = time.perf_counter()
        resp = requests.post(
            f"{self.host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        latency = time.perf_counter() - start
        return resp.json()["response"].strip(), latency

    def list_models(self) -> list[str]:
        resp = requests.get(f"{self.host}/api/tags", timeout=10)
        resp.raise_for_status()
        return [m["name"] for m in resp.json().get("models", [])]
