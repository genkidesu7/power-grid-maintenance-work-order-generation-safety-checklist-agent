# Rule 1 (.claude/rules/test_rule.md): mock_mode_enabled() must be tested
# directly, under every accepted alias, individually, with the others absent.

from src.services.mock_mode import mock_mode_enabled


def test_mock_mode_enabled_via_use_mock(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    assert mock_mode_enabled() is True


def test_mock_mode_enabled_via_stg_mock_mode_alias(monkeypatch):
    """Regression test: deploy-stg sets STG_MOCK_MODE, never USE_MOCK."""
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.setenv("STG_MOCK_MODE", "true")
    assert mock_mode_enabled() is True


def test_mock_mode_disabled_when_neither_set(monkeypatch):
    monkeypatch.delenv("USE_MOCK", raising=False)
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    assert mock_mode_enabled() is False


def test_mock_mode_case_insensitive_and_alt_true_values(monkeypatch):
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    for value in ("1", "TRUE", "yes", "Yes"):
        monkeypatch.setenv("USE_MOCK", value)
        assert mock_mode_enabled() is True, f"expected True for USE_MOCK={value!r}"


def test_mock_mode_false_for_falsy_values(monkeypatch):
    monkeypatch.delenv("STG_MOCK_MODE", raising=False)
    for value in ("false", "0", "no", ""):
        monkeypatch.setenv("USE_MOCK", value)
        assert mock_mode_enabled() is False, f"expected False for USE_MOCK={value!r}"
