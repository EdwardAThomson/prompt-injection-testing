"""Fake-LLM dispatch through the public ai_helper.send_prompt entry.

No network, no SDK clients: the package provider functions are monkeypatched
at the module attribute the facade's registry lambdas resolve at call time.
These tests pin the harness-owned request shape: the security-expert system
prompt (never the package's fiction default), the config.DEFAULT_MODEL
indirection, alias resolution, and the sampling-param omission for the
Claude models that reject temperature.
"""

import llm_backends.multi_provider_llm as mp
import pytest

import ai_helper


@pytest.fixture()
def fake_openai(monkeypatch):
    calls = {}

    def _fake(prompt, model=None, max_tokens=None, temperature=None,
              role_description=None, **kwargs):
        calls.update(prompt=prompt, model=model, max_tokens=max_tokens,
                     temperature=temperature, role_description=role_description)
        return "openai-fake"

    monkeypatch.setattr(mp, "send_prompt_openai", _fake)
    return calls


@pytest.fixture()
def fake_claude(monkeypatch):
    calls = {}

    def _fake(prompt, model=None, max_tokens=None, temperature=0.7,
              role_description=None, **kwargs):
        calls.update(prompt=prompt, model=model, max_tokens=max_tokens,
                     temperature=temperature, role_description=role_description)
        return "claude-fake"

    monkeypatch.setattr(mp, "send_prompt_claude", _fake)
    return calls


@pytest.fixture
def fake_openai_client(monkeypatch):
    """Fake the OpenAI client itself, capturing the exact create() kwargs, so
    the gpt-5.x bare-shape path (which calls the client directly, not
    send_prompt_openai) can be asserted."""
    calls = {}

    class _Msg:
        content = "openai-bare-fake"

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Client:
        class chat:
            class completions:
                @staticmethod
                def create(**kwargs):
                    calls.update(kwargs)
                    return _Resp()

    monkeypatch.setattr(mp, "_get_openai_client", lambda: _Client())
    return calls


def test_default_model_reads_config(fake_openai_client):
    from config import DEFAULT_MODEL

    out = ai_helper.send_prompt("classify this")
    assert out == "openai-bare-fake"
    assert fake_openai_client["model"] == DEFAULT_MODEL


def test_gpt5_keeps_bare_request_shape(fake_openai_client):
    """Measurement fidelity: the gpt-5.x keys must send a single user message
    with no system prompt and no sampling params (the pre-package shape the
    judge is calibrated against). Any drift here changes what PIT measures."""
    out = ai_helper.send_prompt("hello", "gpt-5.5")
    assert out == "openai-bare-fake"
    assert fake_openai_client["model"] == "gpt-5.5"
    assert fake_openai_client["messages"] == [{"role": "user", "content": "hello"}]
    assert "temperature" not in fake_openai_client
    assert "max_tokens" not in fake_openai_client


def test_legacy_alias_resolves_to_primary(fake_claude):
    """The old PIT spelling "claude-haiku-4.5" resolves via the package alias table."""
    out = ai_helper.send_prompt("hello", "claude-haiku-4.5")
    assert out == "claude-fake"
    assert fake_claude["model"] == "claude-haiku-4-5"
    assert fake_claude["temperature"] == 0.7
    assert fake_claude["role_description"] == ai_helper.ROLE_DESCRIPTION


def test_fable_omits_sampling_params(fake_claude):
    ai_helper.send_prompt("hello", "claude-fable-5")
    assert fake_claude["model"] == "claude-fable-5"
    assert fake_claude["temperature"] is None


def test_opus_4_8_omits_sampling_params(fake_claude):
    ai_helper.send_prompt("hello", "claude-opus-4-8")
    assert fake_claude["temperature"] is None


def test_openrouter_prefix_passthrough(monkeypatch):
    calls = {}

    def _fake(prompt, model=None, max_tokens=None, role_description=None, **kwargs):
        calls.update(model=model, role_description=role_description)
        return "or-fake"

    monkeypatch.setattr(mp, "send_prompt_openrouter", _fake)
    out = ai_helper.send_prompt("hello", "openrouter:deepseek/deepseek-chat")
    assert out == "or-fake"
    assert calls["model"] == "deepseek/deepseek-chat"
    assert calls["role_description"] == ai_helper.ROLE_DESCRIPTION


def test_cli_key_routes_to_cli_backend(monkeypatch):
    """CLI registry keys dispatch through cli_backends.send_prompt_cli."""
    import cli_backends

    calls = {}

    def _fake(prompt, backend=None, model=None, **kwargs):
        calls.update(prompt=prompt, backend=backend, model=model)
        return "cli-fake"

    monkeypatch.setattr(cli_backends, "send_prompt_cli", _fake)
    out = ai_helper.send_prompt("hello", "claude-cli-haiku")
    assert out == "cli-fake"
    assert calls["backend"] == "claude-cli"
    assert calls["model"] == "claude-haiku-4-5"


def test_send_prompt_oai_forwards_caller_system_prompt(fake_openai):
    """judge/expand/weak-model pass their own role_description; it must win."""
    ai_helper.send_prompt_oai(
        "user text", model="gpt-5.4-mini", max_tokens=256, temperature=0.0,
        role_description="You are a prompt injection detector.")
    assert fake_openai["role_description"] == "You are a prompt injection detector."
    assert fake_openai["max_tokens"] == 256
    assert fake_openai["temperature"] == 0.0
