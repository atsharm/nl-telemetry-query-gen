import pytest

from src.query_languages import LOGQL
from src.translator import QueryTranslator, build_prompt


def test_build_prompt_includes_examples_and_nl_input():
    prompt = build_prompt(LOGQL, "show me errors")

    assert LOGQL.name in prompt
    assert "show me errors" in prompt
    for nl, query in LOGQL.examples:
        assert nl in prompt
        assert query in prompt


def test_translate_rejects_unsupported_language(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    translator = QueryTranslator()

    with pytest.raises(ValueError, match="Unsupported language"):
        translator.translate("show me errors", "sql")
