"""CLI backend facade over the shared llm-backends package.

The subprocess wrappers that used to live here (an early, unhardened
ScrambleGate-era port) are replaced by the package's HARDENED interfaces
(StoryDaemon docs/LLM_BACKENDS_INVENTORY.md, section 7.4, step 5):

- Provider API keys are stripped from the subprocess environment by default,
  so the CLI's subscription login pays instead of a metered key inherited
  from .env (pass strip_provider_keys=False to a class to opt out).
- Every CLI runs from a neutral empty cwd, so the agent generates text
  instead of acting on this repository.
- codex runs read-only sandboxed with never-prompt approvals (the old copy
  used --dangerously-bypass-approvals-and-sandbox from the repo cwd), plus
  the bubblewrap/user-namespace workaround for hardened Linux hosts.

The class names and the send_prompt_cli / check_cli_availability helpers keep
their old import surface. One capability was dropped: the package's
CodexInterface does not forward a model flag (codex uses the model pinned in
~/.codex/config.toml), so send_prompt_cli(backend="codex", model=...) now
raises instead of silently running a different model.
"""

from typing import Optional

# Re-exports: these ARE the package classes (hardened), not copies.
from llm_backends import (  # noqa: F401
    ClaudeCliInterface,
    CodexInterface,
    GeminiCliInterface,
    check_cli_availability,
)


def send_prompt_cli(prompt: str, backend: str = "claude-cli",
                    model: Optional[str] = None, timeout: int = 120) -> str:
    """Send a prompt via a CLI backend.

    Args:
        prompt: The prompt text.
        backend: One of "claude-cli", "gemini-cli", "codex".
        model: Model name override (claude-cli and gemini-cli only; the codex
            backend runs the model pinned in ~/.codex/config.toml).
        timeout: Timeout in seconds.

    Returns:
        Generated text from the CLI tool.
    """
    if backend == "claude-cli":
        client = ClaudeCliInterface(model=model)
        return client.generate(prompt, timeout=timeout)
    elif backend == "gemini-cli":
        client = GeminiCliInterface(model=model or "gemini-3-flash-preview")
        return client.generate(prompt, timeout=timeout)
    elif backend == "codex":
        if model:
            raise ValueError(
                "The codex CLI backend no longer accepts a model override; it "
                "runs the model pinned in ~/.codex/config.toml. Drop the model "
                "argument, or change the pin there."
            )
        client = CodexInterface()
        return client.generate(prompt, timeout=timeout)
    else:
        raise ValueError(f"Unknown CLI backend: {backend}. Use: claude-cli, gemini-cli, codex")
