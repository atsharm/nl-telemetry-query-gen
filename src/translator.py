"""Translates natural language prompts into telemetry query languages via Claude."""

import os

from anthropic import Anthropic

from .query_languages import SUPPORTED_LANGUAGES, QueryLanguageSpec

DEFAULT_MODEL = "claude-sonnet-5"


def build_prompt(spec: QueryLanguageSpec, nl_prompt: str) -> str:
    examples = "\n".join(
        f'NL: "{nl}"\n{spec.name}: {query}' for nl, query in spec.examples
    )
    return (
        f"You translate natural language into {spec.name} queries.\n\n"
        f"{spec.description}\n\n"
        f"Examples:\n{examples}\n\n"
        f"Respond with ONLY the {spec.name} query on a single line. "
        f"No markdown code fences, no explanation, no extra text.\n\n"
        f'NL: "{nl_prompt}"\n'
        f"{spec.name}: "
    )


def _clean_query(text: str) -> str:
    """Strips markdown code fences and any explanation Claude adds despite
    being told not to, keeping just the first non-empty line/paragraph."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = lines[1:]  # drop opening fence (with optional language tag)
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        elif "```" in lines[-1]:
            lines[-1] = lines[-1].split("```")[0]
        text = "\n".join(lines).strip()
    return text.split("\n\n")[0].strip()


class QueryTranslator:
    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self.model = model

    def translate(self, nl_prompt: str, language: str) -> str:
        language = language.lower()
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. "
                f"Choose from: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        spec = SUPPORTED_LANGUAGES[language]
        prompt = build_prompt(spec, nl_prompt)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        for block in response.content:
            if block.type == "text":
                return _clean_query(block.text)
        raise RuntimeError("No text block in Claude response")

    def translate_all(self, nl_prompt: str) -> dict[str, str]:
        return {
            lang: self.translate(nl_prompt, lang) for lang in SUPPORTED_LANGUAGES
        }
