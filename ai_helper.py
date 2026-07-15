# ai_helper.py
#
# Backward-compatible LLM facade for Prompt-Injection-Testing, now backed by the
# shared `llm-backends` package (StoryDaemon docs/LLM_BACKENDS_INVENTORY.md,
# section 7.4, step 5). Consumers (judge.py, expand.py, gui.py,
# detectors/weak_model_detector.py, detectors/scramblegate/llm_probe.py) keep
# importing send_prompt / send_prompt_oai / get_supported_models from here.
#
# What changed at adoption:
# - ONE model registry: the API model keys are the llm-backends primaries
#   (plus this harness's CLI keys below). The stale 2024/2025-era names
#   (gpt-4o, o1/o3/o4-mini, gemini-1.5/2.0, claude-3-5-*, claude-*-4.6, ...)
#   are gone and now raise ValueError. Package legacy aliases still resolve
#   (e.g. "claude-haiku-4.5" -> "claude-haiku-4-5"), and the
#   "openrouter:<upstream-id>" passthrough form is accepted.
# - The system prompt stays harness-owned (inventory assumption A5): every API
#   call from this facade sends ROLE_DESCRIPTION ("information security
#   expert"), never the package's fiction-writer default.
# - CLI backends route through the package's HARDENED interfaces: provider API
#   keys are stripped from the subprocess env by default (the billing gotcha),
#   the CLI runs from a neutral cwd (so the agent generates text instead of
#   acting on this repo), codex runs read-only sandboxed with the
#   bubblewrap/userns workaround for hardened Linux.
# - The codex CLI no longer takes a per-key model override (the package runs
#   codex on the model pinned in ~/.codex/config.toml), so the old
#   codex-mini / codex-5.3 / codex-5.2 keys are dead.
# - config.DEFAULT_MODEL indirection is unchanged: send_prompt(model=None)
#   still reads the default from config.py at call time.

import os  # noqa: F401  (kept for callers that reach through this module)

from dotenv import load_dotenv

from llm_backends import multi_provider_llm as _mp
from llm_backends.multi_provider_llm import OPENROUTER_PREFIX

load_dotenv()  # App-owned env loading; the package only reads os.environ.


# Harness-owned system prompt (A5): this is a security-testing harness, so the
# package's default role description must never apply to API calls made here.
ROLE_DESCRIPTION = "You are an information security expert."

# Default token ceilings for API calls made through the model registry.
# Callers that need different limits (e.g. the weak-model detector's 256)
# pass them explicitly via send_prompt_oai.
DEFAULT_MAX_TOKENS = 4096
GEMINI_PRO_MAX_TOKENS = 8192

# Claude models that reject sampling params (Fable 5 / Opus 4.8, like Opus
# 4.7): temperature must be omitted (None), not sent, or the API returns 400.
# Mirrors the package registry's own handling; keep the two sets in sync.
_NO_SAMPLING_CLAUDE = {"claude-fable-5", "claude-opus-4-8"}


def _send_openai_bare(prompt, model):
    """Reasoning-style OpenAI call: a single user message, no system prompt and
    no sampling params, reproducing this harness's pre-package gpt-5.x/o-series
    request shape EXACTLY.

    This is a measurement harness, so the request the judge sends must not
    change under the hood: judge.py folds its system prompt into the user
    message for gpt-5 models (it treats them as not supporting a system role),
    so routing these keys through the package's send_prompt_openai (which always
    adds a system message plus temperature/max_tokens) would double the framing
    and shift measured verdicts. The package cannot express the bare shape, so
    it stays local here, exactly as the analyzer keeps its frozen Gemini
    payload local. The openai import is lazy to preserve the SDK-free import
    contract.
    """
    client = _mp._get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
    )
    print("Used model: ", model)
    return response.choices[0].message.content


# --- Model registry ---------------------------------------------------------
#
# API keys mirror the llm-backends primaries but call the package provider
# functions directly so ROLE_DESCRIPTION is this harness's, not the package
# default (the package registry lambdas do not thread role_description).
# A test asserts the package primaries are all covered here, so a package
# registry bump shows up as a test failure instead of silent drift.
_model_config = {
    # OpenAI GPT-5 family
    # The gpt-5.x keys keep the harness's original bare (user-only) request
    # shape via _send_openai_bare; see that helper for why the package path
    # would change what the judge measures.
    "gpt-5.5": lambda prompt: _send_openai_bare(prompt, "gpt-5.5"),
    "gpt-5.4": lambda prompt: _send_openai_bare(prompt, "gpt-5.4"),
    "gpt-5.4-mini": lambda prompt: _send_openai_bare(prompt, "gpt-5.4-mini"),
    "gpt-5.2": lambda prompt: _send_openai_bare(prompt, "gpt-5.2"),
    # Anthropic Claude family (temperature=None for the sampling-param-free models)
    "claude-fable-5": lambda prompt: _mp.send_prompt_claude(
        prompt, model="claude-fable-5", max_tokens=DEFAULT_MAX_TOKENS,
        temperature=None, role_description=ROLE_DESCRIPTION),
    "claude-opus-4-8": lambda prompt: _mp.send_prompt_claude(
        prompt, model="claude-opus-4-8", max_tokens=DEFAULT_MAX_TOKENS,
        temperature=None, role_description=ROLE_DESCRIPTION),
    "claude-sonnet-4-6": lambda prompt: _mp.send_prompt_claude(
        prompt, model="claude-sonnet-4-6", max_tokens=DEFAULT_MAX_TOKENS,
        temperature=0.7, role_description=ROLE_DESCRIPTION),
    # Dated snapshot id mirrors the package registry entry for this key.
    "claude-sonnet-4-5": lambda prompt: _mp.send_prompt_claude(
        prompt, model="claude-sonnet-4-5-20250929", max_tokens=DEFAULT_MAX_TOKENS,
        temperature=0.7, role_description=ROLE_DESCRIPTION),
    "claude-haiku-4-5": lambda prompt: _mp.send_prompt_claude(
        prompt, model="claude-haiku-4-5", max_tokens=DEFAULT_MAX_TOKENS,
        temperature=0.7, role_description=ROLE_DESCRIPTION),
    # Google Gemini (the package Gemini path sends no system prompt, matching
    # this harness's previous behavior; callers combine system+user themselves)
    "gemini-3.1-pro-preview": lambda prompt: _mp.send_prompt_gemini(
        prompt, model_name="gemini-3.1-pro-preview",
        max_output_tokens=GEMINI_PRO_MAX_TOKENS, temperature=0.7),
    "gemini-3.1-flash-preview": lambda prompt: _mp.send_prompt_gemini(
        prompt, model_name="gemini-3.1-flash-preview",
        max_output_tokens=DEFAULT_MAX_TOKENS, temperature=0.7),
    "gemini-3-pro-preview": lambda prompt: _mp.send_prompt_gemini(
        prompt, model_name="gemini-3-pro-preview",
        max_output_tokens=GEMINI_PRO_MAX_TOKENS, temperature=0.7),
    "gemini-3-flash-preview": lambda prompt: _mp.send_prompt_gemini(
        prompt, model_name="gemini-3-flash-preview",
        max_output_tokens=DEFAULT_MAX_TOKENS, temperature=0.7),
    "gemini-2.5-pro": lambda prompt: _mp.send_prompt_gemini(
        prompt, model_name="gemini-2.5-pro",
        max_output_tokens=GEMINI_PRO_MAX_TOKENS, temperature=0.7),
    "gemini-2.5-flash": lambda prompt: _mp.send_prompt_gemini(
        prompt, model_name="gemini-2.5-flash",
        max_output_tokens=DEFAULT_MAX_TOKENS, temperature=0.7),
    # Env-configured providers (model chosen by *_MODEL env vars; see the
    # llm-backends README). Errors are loud when the env is not set.
    "hosted-llm": lambda prompt: _mp.send_prompt_hosted_llm(
        prompt, max_tokens=DEFAULT_MAX_TOKENS, role_description=ROLE_DESCRIPTION),
    "openrouter": lambda prompt: _mp.send_prompt_openrouter(
        prompt, max_tokens=DEFAULT_MAX_TOKENS, role_description=ROLE_DESCRIPTION),
    "venice": lambda prompt: _mp.send_prompt_venice(
        prompt, max_tokens=DEFAULT_MAX_TOKENS, role_description=ROLE_DESCRIPTION),
    # OpenRouter convenience keys; any other OpenRouter model works via the
    # "openrouter:<upstream-id>" passthrough form (no registry change needed).
    "openrouter-deepseek": lambda prompt: _mp.send_prompt_openrouter(
        prompt, model="deepseek/deepseek-chat", max_tokens=DEFAULT_MAX_TOKENS,
        role_description=ROLE_DESCRIPTION),
    "openrouter-haiku": lambda prompt: _mp.send_prompt_openrouter(
        prompt, model="anthropic/claude-haiku-4.5", max_tokens=DEFAULT_MAX_TOKENS,
        role_description=ROLE_DESCRIPTION),
    # CLI backends (no API keys required; uses local CLI tools via the
    # package's hardened interfaces: key-stripping, neutral cwd).
    "claude-cli": lambda prompt: _send_prompt_cli("claude-cli", prompt),
    "claude-cli-opus": lambda prompt: _send_prompt_cli("claude-cli", prompt, model="claude-opus-4-8"),
    "claude-cli-sonnet": lambda prompt: _send_prompt_cli("claude-cli", prompt, model="claude-sonnet-4-6"),
    "claude-cli-haiku": lambda prompt: _send_prompt_cli("claude-cli", prompt, model="claude-haiku-4-5"),
    "claude-cli-fable": lambda prompt: _send_prompt_cli("claude-cli", prompt, model="claude-fable-5"),
    "gemini-cli": lambda prompt: _send_prompt_cli("gemini-cli", prompt),
    "gemini-cli-pro": lambda prompt: _send_prompt_cli("gemini-cli", prompt, model="gemini-3-pro-preview"),
    "gemini-cli-3.1-pro": lambda prompt: _send_prompt_cli("gemini-cli", prompt, model="gemini-3.1-pro-preview"),
    "gemini-cli-2.5-pro": lambda prompt: _send_prompt_cli("gemini-cli", prompt, model="gemini-2.5-pro"),
    # Codex CLI: runs the model pinned in ~/.codex/config.toml. The old
    # codex-mini / codex-5.3 / codex-5.2 override keys are gone (the hardened
    # interface does not forward a model flag).
    "codex": lambda prompt: _send_prompt_cli("codex", prompt),
}
# --- End Model Configurations ---


def _send_prompt_cli(backend: str, prompt: str, model: str = None) -> str:
    """Route to a CLI backend. Lazy-imports so API-only use never needs the CLIs."""
    from cli_backends import send_prompt_cli
    return send_prompt_cli(prompt, backend=backend, model=model)


def get_supported_models():
    """Returns a list of supported model names."""
    return list(_model_config.keys())


def _resolve(model: str) -> str:
    """Resolve a model name to a registry key (or an openrouter: passthrough).

    Accepts registry keys, the package's legacy aliases (e.g.
    "claude-haiku-4.5"), a "-latest" suffix fallback, and the
    "openrouter:<upstream-id>" form. Raises ValueError for dead names, listing
    the supported set (same error behavior the old registry had).
    """
    if model in _model_config:
        return model
    if model.startswith(OPENROUTER_PREFIX):
        # Validates the upstream id is non-empty; returned verbatim.
        return _mp.resolve_model(model)
    try:
        resolved = _mp.resolve_model(model)
    except ValueError:
        resolved = None
    if resolved in _model_config:
        return resolved
    raise ValueError(
        f"Unsupported model: {model}. Supported models are: {get_supported_models()}"
    )


def send_prompt(prompt, model=None):
    """Sends a prompt to the specified AI model.

    model=None reads config.DEFAULT_MODEL at call time (kept indirection).
    """
    if model is None:
        from config import DEFAULT_MODEL
        model = DEFAULT_MODEL

    model = _resolve(model)

    print(f"Attempting to use model: {model}")
    try:
        if model.startswith(OPENROUTER_PREFIX):
            upstream = model[len(OPENROUTER_PREFIX):]
            return _mp.send_prompt_openrouter(
                prompt, model=upstream, max_tokens=DEFAULT_MAX_TOKENS,
                role_description=ROLE_DESCRIPTION)
        return _model_config[model](prompt)
    except Exception as e:
        print(f"Error calling model '{model}': {e}")
        raise  # Re-raise; callers own their retry policy.


# --- Provider-specific helpers (kept import surface, package-backed) ---------


def send_prompt_oai(prompt, model=None, max_tokens=1500, temperature=0.7,
                    role_description=ROLE_DESCRIPTION):
    """Send a prompt to an OpenAI chat model with an explicit system prompt.

    Used by judge/expand/weak-model paths that pass their own role_description.
    """
    if model is None:
        from config import DEFAULT_MODEL
        model = DEFAULT_MODEL
    return _mp.send_prompt_openai(
        prompt, model=model, max_tokens=max_tokens, temperature=temperature,
        role_description=role_description)


def send_prompt_o1(prompt, model=None):
    """Legacy o-series helper: the bare (user-only) request shape, preserved.

    The o1/o3/o4 registry keys are retired, but callers that import this
    function expect the reasoning-style call with no system prompt, so it keeps
    that shape (via _send_openai_bare) against config.DEFAULT_MODEL when no
    model is given, rather than silently gaining a system prompt."""
    if model is None:
        from config import DEFAULT_MODEL
        model = DEFAULT_MODEL
    return _send_openai_bare(prompt, model)


def send_prompt_gemini(prompt, model_name="gemini-2.5-pro", max_output_tokens=1024,
                       temperature=0.9, top_p=1, top_k=1):
    """Send a prompt to the Gemini API (package-backed).

    top_p / top_k are accepted for signature compatibility but no longer
    forwarded (the shared package's Gemini path does not send them).
    """
    return _mp.send_prompt_gemini(
        prompt, model_name=model_name, max_output_tokens=max_output_tokens,
        temperature=temperature)


def send_prompt_claude(prompt, model="claude-sonnet-4-6", max_tokens=4096,
                       temperature=0.7, role_description=ROLE_DESCRIPTION):
    """Send a prompt to Anthropic Claude (package-backed).

    Note: unlike the pre-adoption copy this raises on API errors instead of
    returning None (send_prompt's callers already handled exceptions).
    For claude-fable-5 / claude-opus-4-8 pass temperature=None.
    """
    return _mp.send_prompt_claude(
        prompt, model=model, max_tokens=max_tokens, temperature=temperature,
        role_description=role_description)
