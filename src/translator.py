"""Translates natural language prompts into telemetry query languages via Claude."""

import os

from anthropic import Anthropic

from .query_languages import SUPPORTED_LANGUAGES, QueryLanguageSpec

DEFAULT_MODEL = "claude-sonnet-5"


def _build_prompt(spec: QueryLanguageSpec, nl_prompt: str) -> str:
    examples = "\n".join(
        f'NL: "{nl}"\n{spec.name}: {query}' for nl, query in spec.examples
    )
    return (
        f"You translate natural language into {spec.name} queries.\n\n"
        f"{spec.description}\n\n"
        f"Examples:\n{examples}\n\n"
        f'NL: "{nl_prompt}"\n'
        f"{spec.name}: "
    )


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
        prompt = _build_prompt(spec, nl_prompt)

        response = self.client.messages.create(
            model=self.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def translate_all(self, nl_prompt: str) -> dict[str, str]:
        return {
            lang: self.translate(nl_prompt, lang) for lang in SUPPORTED_LANGUAGES
        }
