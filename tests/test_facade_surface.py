"""Facade import-surface checks for the llm-backends adoption.

Every name the harness's consumers import (judge.py, expand.py, gui.py,
detectors/weak_model_detector.py, detectors/scramblegate/llm_probe.py) must
keep working, and the CLI classes re-exported from cli_backends must BE the
package's hardened classes, not copies.
"""

import llm_backends


def test_ai_helper_public_surface():
    from ai_helper import (  # noqa: F401
        ROLE_DESCRIPTION,
        get_supported_models,
        send_prompt,
        send_prompt_claude,
        send_prompt_gemini,
        send_prompt_o1,
        send_prompt_oai,
    )

    assert ROLE_DESCRIPTION == "You are an information security expert."


def test_cli_backends_classes_are_package_classes():
    import cli_backends

    assert cli_backends.ClaudeCliInterface is llm_backends.ClaudeCliInterface
    assert cli_backends.CodexInterface is llm_backends.CodexInterface
    assert cli_backends.GeminiCliInterface is llm_backends.GeminiCliInterface
    assert cli_backends.check_cli_availability is llm_backends.check_cli_availability


def test_cli_backends_send_prompt_cli_surface():
    from cli_backends import send_prompt_cli  # noqa: F401


def test_supported_models_cover_package_primaries():
    """Every package registry primary is dispatchable through the facade, so a
    package registry bump surfaces here instead of drifting silently."""
    import ai_helper

    facade = set(ai_helper.get_supported_models())
    assert set(llm_backends.get_supported_models()) <= facade


def test_supported_models_include_cli_keys():
    import ai_helper

    facade = set(ai_helper.get_supported_models())
    expected_cli = {
        "claude-cli", "claude-cli-opus", "claude-cli-sonnet",
        "claude-cli-haiku", "claude-cli-fable",
        "gemini-cli", "gemini-cli-pro", "gemini-cli-3.1-pro",
        "gemini-cli-2.5-pro",
        "codex",
    }
    assert expected_cli <= facade


def test_config_default_models_resolve():
    """config.DEFAULT_MODEL indirection: both defaults must be live registry keys."""
    import ai_helper
    from config import DEFAULT_MODEL, DEFAULT_WEAK_MODEL

    supported = ai_helper.get_supported_models()
    assert DEFAULT_MODEL in supported
    assert DEFAULT_WEAK_MODEL in supported


def test_weak_model_safe_list_resolves():
    """The weak-model detector's no-tool-call model list must stay live."""
    import ai_helper
    from detectors.weak_model_detector import SAFE_MODELS

    supported = set(ai_helper.get_supported_models())
    assert set(SAFE_MODELS) <= supported
