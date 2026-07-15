"""Dead-name error behavior.

Every stale pre-adoption registry key that has no package primary or alias
must raise ValueError from the public send_prompt entry, before any network
or SDK client is touched, and must list the supported set (the old registry's
error contract). None of them may appear in get_supported_models().
"""

import pytest

import ai_helper

DEAD_NAMES = [
    # OpenAI, 2024/2025-era
    "gpt-4o", "gpt-4o-mini", "o1", "o1-mini", "o3", "o4-mini",
    "gpt-5", "gpt-5.2-codex", "gpt-5.3-codex",
    # Gemini, 1.5/2.0/2.5-exp era
    "gemini-1.5-pro-latest", "gemini-2.0-pro-exp-02-05",
    "gemini-2.5-pro-exp-03-25", "gemini-2.0-flash",
    # Claude 3.x era and the 4.6 spellings with no package alias
    "claude-3-5-sonnet", "claude-3-7-sonnet", "claude-3-5-haiku",
    "claude-sonnet-4.6", "claude-opus-4.6",
    # Codex CLI model-override keys (the hardened codex interface runs the
    # ~/.codex pinned model only)
    "codex-mini", "codex-5.3", "codex-5.2",
]


@pytest.mark.parametrize("dead", DEAD_NAMES)
def test_dead_name_raises_value_error(dead):
    with pytest.raises(ValueError) as excinfo:
        ai_helper.send_prompt("hello", dead)
    msg = str(excinfo.value)
    assert dead in msg
    assert "Supported models are" in msg


@pytest.mark.parametrize("dead", DEAD_NAMES)
def test_dead_name_not_listed(dead):
    assert dead not in ai_helper.get_supported_models()


def test_empty_openrouter_passthrough_rejected():
    with pytest.raises(ValueError):
        ai_helper.send_prompt("hello", "openrouter:")


def test_codex_model_override_rejected_at_cli_layer():
    """cli_backends refuses a codex model override instead of silently
    running a different model than requested."""
    import cli_backends

    with pytest.raises(ValueError, match="model override"):
        cli_backends.send_prompt_cli("hello", backend="codex", model="gpt-5.4-mini")
