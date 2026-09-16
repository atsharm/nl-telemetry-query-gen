# Natural Language Telemetry Query Generator

A tool that translates plain-English descriptions of what you want to observe
("show me 5xx errors from checkout in the last hour") into three different
telemetry query languages — **LogQL** (Grafana Loki), **PromQL**
(Prometheus), and **MQL** (OCI Monitoring Query Language) — and benchmarks
how well small local LLMs (via [Ollama](https://ollama.com)) do at the same
task compared to Claude.

Built to explore two things: (1) whether a single NL prompt can be reliably
fanned out into multiple query grammars with few-shot prompting alone, and
(2) how far a 0.5B–4B local model can be pushed on a narrow, structured
generation task before it needs a frontier model.

---

## High-Level Overview

### What it does
1. You type a natural language query intent into a Streamlit UI.
2. The app sends that prompt to Claude three times — once per query
   language — each time with a few-shot prompt that teaches Claude the
   target grammar via a short spec and 1-2 examples.
3. Claude returns three queries (LogQL, PromQL, MQL) side by side.
4. Separately, a benchmarking script runs the same prompts through local
   Ollama models and Claude, records latency, and saves results to JSON
   that the UI can visualize (average latency per model, per-row outputs).

### Why these three languages
LogQL, PromQL, and MQL cover the three telemetry pillars (logs, metrics,
cloud-provider metrics) and have meaningfully different grammars — bracket
selectors and pipe filters (LogQL), function-wrapped metric selectors
(PromQL), and a namespace/dimension/aggregation chain (MQL). Getting a
single prompting approach to generalize across all three is the interesting
part of this project.

### Why benchmark local models
Frontier APIs cost money and have network latency per call. If a 0.5B–4B
local model can produce syntactically valid queries for common cases, a
production version of this tool could route simple queries locally and
reserve Claude for ambiguous or complex ones. The benchmark measures
whether that tradeoff is viable — comparing latency and, informally, output
quality across models.

### Architecture at a glance

```
┌─────────────────┐      ┌───────────────────┐      ┌──────────────────┐
│   Streamlit UI   │─────▶│  QueryTranslator   │─────▶│   Anthropic API   │
│    (src/app.py)  │      │ (src/translator.py)│      │  (Claude Sonnet)  │
└─────────────────┘      └───────────────────┘      └──────────────────┘
         │
         │ loads saved runs from
         ▼
┌──────────────────────┐      ┌──────────────────┐      ┌───────────────┐
│  benchmark_results/   │◀─────│  src/benchmark.py │─────▶│ OllamaClient  │
│      *.json           │      │                    │      │ (local models)│
└──────────────────────┘      └──────────────────┘      └───────────────┘
```

Both the live translation path and the offline benchmark path share the
same prompt-building logic (`translator.build_prompt`) and the same query
language specs (`query_languages.py`), so a benchmarked local model is
being tested on literally the same prompt Claude would receive — not a
simplified version.

---

## Implementation Details

### `src/query_languages.py` — the grammar layer
Each query language is a `QueryLanguageSpec`: a name, a short prose
description of its grammar, and a small list of `(natural_language, query)`
example pairs. This is the only place that knows what LogQL/PromQL/MQL look
like — everything downstream (translator, benchmark) is language-agnostic
and just iterates over `SUPPORTED_LANGUAGES`. Adding a fourth query language
means adding one `QueryLanguageSpec` here; nothing else changes.

### `src/translator.py` — the Claude path
`build_prompt(spec, nl_prompt)` assembles a few-shot prompt: the spec's
description, its worked examples, then the user's NL input with the target
language name as a completion cue (e.g. `LogQL: `). This is deliberately a
plain string-completion style prompt rather than a chat-turn-heavy one,
since the task is narrow (structured text generation) and few-shot examples
do most of the grounding work.

`QueryTranslator.translate(nl_prompt, language)` builds that prompt, calls
`messages.create` against the configured Claude model, and returns the raw
text response with whitespace stripped. `translate_all()` just calls
`translate()` once per supported language — this is what the UI's
"Translate" button uses to populate all three columns in one action.

The API key is read from `ANTHROPIC_API_KEY` at construction time (via
`os.environ` or an explicit `api_key` arg), not at call time, so a missing
key fails fast with a clear `KeyError` rather than deep inside a request.

### `src/ollama_client.py` — the local-model path
A deliberately thin wrapper — two methods, no retry/streaming logic. Ollama
runs as a local HTTP server (started via `brew services start ollama` or
`ollama serve`); `generate()` POSTs to `/api/generate` with
`"stream": false` so the full response comes back in one payload instead of
needing to consume a streamed response, and times the call with
`time.perf_counter()` so latency numbers reflect wall-clock request time,
not token-generation time reported by the model itself (which can be
misleading when comparing across very different model sizes).

### `src/benchmark.py` — the comparison harness
`run_benchmark()` is a triple nested loop: for each prompt in
`BENCHMARK_PROMPTS`, for each query language, it builds one prompt via the
shared `build_prompt()` helper and sends that identical prompt to Claude
(if `include_claude=True`) and to every model in `ollama_models`. Every
result row records `model`, `source` (`"claude"` or `"ollama"`),
`language`, the original `prompt`, the generated `query`, and
`latency_seconds` — a flat, denormalized structure chosen specifically so
it can be dropped straight into `st.dataframe()` / aggregated with a
one-line `groupby`-style loop in the UI without a separate transformation
step.

`save_results()` writes each run to a UTC-timestamped JSON file under
`benchmark_results/`, so repeated runs accumulate as a history rather than
overwriting each other — useful for tracking whether a newly pulled model
or a prompt tweak changed latency or output quality over time. That
directory is gitignored (raw benchmark output is a local artifact, not
something to version).

Run standalone via:
```bash
python -m src.benchmark
```
This auto-discovers currently pulled Ollama models via `list_models()`
rather than hardcoding model names, so the benchmark stays in sync with
whatever you've actually pulled.

### `src/app.py` — the UI
Two tabs, deliberately kept separate:
- **Translate**: a single text input and button, calling
  `translator.translate_all()` live and rendering each language's output
  in its own column via `st.code()`. This is the "demo" surface.
- **Benchmark Results**: reads saved JSON files from `benchmark_results/`
  (no live model calls), lets you pick a run from a dropdown, shows the raw
  rows in a dataframe, and computes average latency per model with a small
  in-memory aggregation before rendering `st.bar_chart()`. Kept separate
  from the Translate tab because benchmark runs take much longer than a
  single translation and shouldn't block the interactive demo path.

### Tests (`tests/`)
Tests intentionally avoid live network calls (no Anthropic or Ollama calls
in CI): `test_query_languages.py` checks the language registry's shape and
that every example pair is non-empty; `test_translator.py` checks prompt
construction (that the spec's examples and the user's NL input actually
land in the final prompt string) and that an unsupported language raises
`ValueError` before any API call is attempted. The `ANTHROPIC_API_KEY` env
var is monkeypatched to a dummy value in tests that construct a
`QueryTranslator`, since the constructor requires the key to be present but
these tests never actually call the API.

---

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # then fill in ANTHROPIC_API_KEY

brew install ollama
brew services start ollama
ollama pull qwen2.5:0.5b
ollama pull phi3:mini
```

## Running

```bash
# Interactive UI
streamlit run src/app.py

# Benchmark local models vs Claude, saves timestamped JSON
python -m src.benchmark

# Tests
pytest tests/ -v
```

## Possible next steps
- Structured accuracy scoring against a fixed eval set (right now the
  benchmark only measures latency, not correctness)
- Streaming responses in the UI instead of waiting for full completions
- A fourth query language (e.g. SQL-based query languages like KQL) to
  test how well the few-shot approach generalizes beyond the three built in
