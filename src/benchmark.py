"""Benchmarks local Ollama models against Claude on NL-to-query translation.

For each (prompt, language, model) combination, records the generated query
and latency, then writes results to a JSON file for later inspection in the
Streamlit UI.
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

from .ollama_client import OllamaClient
from .query_languages import SUPPORTED_LANGUAGES
from .translator import QueryTranslator, build_prompt

BENCHMARK_PROMPTS = [
    "show me error logs from the payments service in the last 15 minutes",
    "request rate for the api service over the last 5 minutes",
    "average cpu utilization over the last minute",
]

RESULTS_DIR = Path(__file__).resolve().parent.parent / "benchmark_results"


def run_benchmark(
    ollama_models: list[str],
    prompts: list[str] = BENCHMARK_PROMPTS,
    include_claude: bool = True,
) -> list[dict]:
    ollama = OllamaClient()
    translator = QueryTranslator() if include_claude else None

    results = []
    for nl_prompt in prompts:
        for lang_key, spec in SUPPORTED_LANGUAGES.items():
            full_prompt = build_prompt(spec, nl_prompt)

            if include_claude:
                start = time.perf_counter()
                query = translator.translate(nl_prompt, lang_key)
                latency = time.perf_counter() - start
                results.append(
                    {
                        "model": translator.model,
                        "source": "claude",
                        "language": lang_key,
                        "prompt": nl_prompt,
                        "query": query,
                        "latency_seconds": round(latency, 3),
                    }
                )

            for model in ollama_models:
                query, latency = ollama.generate(model, full_prompt)
                results.append(
                    {
                        "model": model,
                        "source": "ollama",
                        "language": lang_key,
                        "prompt": nl_prompt,
                        "query": query,
                        "latency_seconds": round(latency, 3),
                    }
                )
    return results


def save_results(results: list[dict]) -> Path:
    RESULTS_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = RESULTS_DIR / f"benchmark_{timestamp}.json"
    out_path.write_text(json.dumps(results, indent=2))
    return out_path


if __name__ == "__main__":
    models = OllamaClient().list_models()
    results = run_benchmark(ollama_models=models)
    path = save_results(results)
    print(f"Wrote {len(results)} results to {path}")
