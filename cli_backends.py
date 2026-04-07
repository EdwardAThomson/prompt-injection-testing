"""CLI backend interfaces for sending prompts to AI via local CLI tools.

Provides subprocess-based wrappers for:
- claude (Claude Code CLI) - supports: claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5
- gemini (Gemini CLI) - supports: gemini-3-flash-preview, gemini-3-pro-preview, gemini-3.1-pro-preview, gemini-2.5-pro, gemini-2.5-flash
- codex (OpenAI Codex CLI) - supports: gpt-5.4 (only model with ChatGPT accounts)

These are an alternative to the API-based functions in ai_helper.py.
No API keys required - uses whatever CLI tools are installed locally.

CLI version requirements:
- Gemini CLI: @google/gemini-cli >= 0.36.0
- Codex CLI: @openai/codex >= 0.118.0
- Claude Code: any recent version

Adapted from NovelWriter (~/Projects/NovelWriter).
"""

import json
import shutil
import subprocess
from typing import Optional


# ── Claude Code CLI ───────────────────────────────────────────────────

class ClaudeCliInterface:
    """Interface for calling Claude Code CLI in headless mode.

    Invokes: claude -p "<prompt>" --output-format json [--model <model>]

    Supported models: claude-opus-4-6 (default), claude-sonnet-4-6, claude-haiku-4-5
    """

    SUPPORTED_MODELS = ["claude-opus-4-6", "claude-sonnet-4-6", "claude-haiku-4-5"]

    def __init__(self, claude_bin: str = "claude", model: Optional[str] = None):
        self.claude_bin = claude_bin
        self.model = model  # None = use CLI default (opus)
        if not self.is_available(claude_bin):
            raise RuntimeError(
                f"Claude Code CLI not found at '{claude_bin}'. "
                "Install from https://github.com/anthropics/claude-code"
            )

    @staticmethod
    def is_available(claude_bin: str = "claude") -> bool:
        return shutil.which(claude_bin) is not None

    def generate(self, prompt: str, max_tokens: int = 2000, timeout: int = 120) -> str:
        cmd = [self.claude_bin, "-p", prompt, "--output-format", "json"]
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout, check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Claude CLI error: {e.stderr.strip() or 'Unknown'}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Claude CLI timed out after {timeout}s")

        stdout = result.stdout.strip()
        if not stdout:
            raise RuntimeError("Claude CLI returned empty output")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse Claude CLI JSON: {e}") from e

        if isinstance(data, dict):
            if data.get("is_error"):
                raise RuntimeError(f"Claude CLI error: {data.get('result', 'Unknown error')}")
            if "result" in data:
                return str(data["result"])

        raise RuntimeError("Claude CLI JSON missing 'result' field")

    def generate_with_retry(self, prompt: str, max_tokens: int = 2000,
                            timeout: int = 120, max_retries: int = 3) -> str:
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.generate(prompt, max_tokens, timeout)
            except RuntimeError as e:
                last_error = e
        raise RuntimeError(f"Claude CLI failed after {max_retries} attempts: {last_error}")


# ── Gemini CLI ────────────────────────────────────────────────────────

class GeminiCliInterface:
    """Interface for calling Gemini CLI.

    Invokes via stdin: echo "<prompt>" | gemini [-m <model>]

    Supported models (Gemini CLI v0.36.0+):
      gemini-3-flash-preview (default), gemini-3-pro-preview, gemini-3.1-pro-preview,
      gemini-3.1-flash-lite-preview, gemini-2.5-pro, gemini-2.5-flash, gemini-2.5-flash-lite
    """

    SUPPORTED_MODELS = [
        "gemini-3-flash-preview", "gemini-3-pro-preview",
        "gemini-3.1-pro-preview", "gemini-3.1-flash-lite-preview",
        "gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.5-flash-lite",
    ]

    def __init__(self, model: str = "gemini-3-flash-preview", gemini_bin: str = "gemini"):
        self.model = model
        self.gemini_bin = gemini_bin
        if not self.is_available(gemini_bin):
            raise RuntimeError(
                f"Gemini CLI not found at '{gemini_bin}'. "
                "Install from https://github.com/google-gemini/gemini-cli"
            )

    @staticmethod
    def is_available(gemini_bin: str = "gemini") -> bool:
        return shutil.which(gemini_bin) is not None

    def generate(self, prompt: str, max_tokens: int = 2000, timeout: int = 120) -> str:
        try:
            # Use stdin pipe (positional/stdin is the supported input method)
            result = subprocess.run(
                [self.gemini_bin, "-m", self.model],
                input=prompt,
                capture_output=True, text=True, timeout=timeout, check=True,
            )
            # stdout may contain the response; stderr has deprecation warnings
            output = result.stdout.strip()
            if not output:
                raise RuntimeError("Gemini CLI returned empty output")
            return output
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else "Unknown error"
            # Filter out node deprecation warnings from actual errors
            error_lines = [
                line for line in error_msg.split('\n')
                if 'DeprecationWarning' not in line and 'node --trace' not in line
            ]
            raise RuntimeError(f"Gemini CLI error: {' '.join(error_lines)}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Gemini CLI timed out after {timeout}s")

    def generate_with_retry(self, prompt: str, max_tokens: int = 2000,
                            timeout: int = 120, max_retries: int = 3) -> str:
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.generate(prompt, max_tokens, timeout)
            except RuntimeError as e:
                last_error = e
        raise RuntimeError(f"Gemini CLI failed after {max_retries} attempts: {last_error}")


# ── Codex CLI (OpenAI GPT-5.4) ───────────────────────────────────────

class CodexInterface:
    """Interface for calling Codex CLI for GPT-5.4 access.

    Invokes: codex exec -m <model> --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check <prompt>

    Models available via Codex CLI (v0.118.0):
      gpt-5.4 (default), gpt-5.4-mini, gpt-5.3-codex, gpt-5.2-codex, gpt-5.2
    Note: o3/o4-mini are NOT supported with ChatGPT accounts.
    """

    SUPPORTED_MODELS = [
        "gpt-5.4", "gpt-5.4-mini", "gpt-5.3-codex", "gpt-5.2-codex", "gpt-5.2",
    ]

    def __init__(self, codex_bin: str = "codex", model: Optional[str] = None):
        self.codex_bin = codex_bin
        self.model = model  # None = use CLI default (gpt-5.4)
        if not self.is_available(codex_bin):
            raise RuntimeError(
                f"Codex CLI not found at '{codex_bin}'. "
                "Install with: npm install -g @openai/codex"
            )

    @staticmethod
    def is_available(codex_bin: str = "codex") -> bool:
        return shutil.which(codex_bin) is not None

    def generate(self, prompt: str, max_tokens: int = 2000, timeout: int = 120) -> str:
        cmd = [self.codex_bin, "exec",
               "--dangerously-bypass-approvals-and-sandbox",
               "--skip-git-repo-check"]
        if self.model:
            cmd.extend(["-m", self.model])
        cmd.append(prompt)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=timeout, check=True,
            )
            # Codex outputs a verbose banner before the actual response.
            # The response text is the last non-empty line(s) after "codex" marker.
            return self._parse_codex_output(result.stdout)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Codex CLI error: {e.stderr.strip() or 'Unknown'}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Codex CLI timed out after {timeout}s")

    def _parse_codex_output(self, stdout: str) -> str:
        """Extract the actual response from Codex's verbose output.

        Codex output format:
            OpenAI Codex v0.115.0 ...
            --------
            ... banner lines ...
            --------
            user
            <prompt>
            mcp startup: ...
            codex
            <response>
            tokens used
            <count>
            <response again>

        We take the text between the last 'codex' marker and the 'tokens used' line.
        """
        lines = stdout.strip().split('\n')

        # Find the last 'codex' line (marks start of response)
        codex_idx = None
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() == 'codex':
                codex_idx = i
                break

        if codex_idx is not None:
            # Collect lines after 'codex' until 'tokens used'
            response_lines = []
            for line in lines[codex_idx + 1:]:
                if line.strip() == 'tokens used':
                    break
                response_lines.append(line)
            if response_lines:
                return '\n'.join(response_lines).strip()

        # Fallback: return the last non-empty line
        for line in reversed(lines):
            stripped = line.strip()
            if stripped and not stripped.startswith('OpenAI') and stripped != '--------':
                return stripped
        return stdout.strip()

    def generate_with_retry(self, prompt: str, max_tokens: int = 2000,
                            timeout: int = 120, max_retries: int = 3) -> str:
        last_error = None
        for attempt in range(max_retries):
            try:
                return self.generate(prompt, max_tokens, timeout)
            except RuntimeError as e:
                last_error = e
        raise RuntimeError(f"Codex CLI failed after {max_retries} attempts: {last_error}")


# ── Utility functions ─────────────────────────────────────────────────

def check_cli_availability() -> dict:
    """Check which CLI tools are available on this system."""
    return {
        "claude-cli": ClaudeCliInterface.is_available(),
        "gemini-cli": GeminiCliInterface.is_available(),
        "codex": CodexInterface.is_available(),
    }


def send_prompt_cli(prompt: str, backend: str = "claude-cli",
                    model: Optional[str] = None, timeout: int = 120) -> str:
    """Send a prompt via a CLI backend.

    Args:
        prompt: The prompt text.
        backend: One of "claude-cli", "gemini-cli", "codex".
        model: Model name override (claude-cli and gemini-cli only).
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
        client = CodexInterface(model=model)
        return client.generate(prompt, timeout=timeout)
    else:
        raise ValueError(f"Unknown CLI backend: {backend}. Use: claude-cli, gemini-cli, codex")
