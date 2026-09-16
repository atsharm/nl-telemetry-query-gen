from src.query_languages import SUPPORTED_LANGUAGES


def test_all_languages_have_examples():
    for spec in SUPPORTED_LANGUAGES.values():
        assert len(spec.examples) >= 1
        for nl, query in spec.examples:
            assert nl.strip()
            assert query.strip()


def test_expected_languages_present():
    assert set(SUPPORTED_LANGUAGES.keys()) == {"logql", "promql", "mql"}
