"""Key-strip regression for one CLI path (the billing gotcha).

ai_helper runs load_dotenv(), so provider API keys from .env sit in
os.environ; the agent CLIs treat an environment API key as outranking their
configured subscription login. The package CLI interfaces therefore strip the
provider keys from a COPY of the subprocess environment by default. This
drives the claude-cli path through this repo's cli_backends facade with a
fake subprocess and asserts the child env.
"""

import json
import os

import pytest

import cli_backends


class FakeCompleted:
    def __init__(self, stdout):
        self.stdout = stdout
        self.stderr = ""
        self.returncode = 0


@pytest.fixture()
def captured_run(monkeypatch):
    """Fake subprocess.run inside the package module, capturing kwargs."""
    import llm_backends.claude_cli_interface as mod

    captured = {}

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env")
        captured["cwd"] = kwargs.get("cwd")
        return FakeCompleted(json.dumps({"result": "stripped ok"}))

    monkeypatch.setattr(mod.shutil, "which", lambda _bin: "/usr/bin/claude")
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    return captured


def test_claude_cli_strips_anthropic_keys(monkeypatch, captured_run):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-metered")
    monkeypatch.setenv("CLAUDE_API_KEY", "sk-ant-legacy")

    out = cli_backends.send_prompt_cli(
        "write a line", backend="claude-cli", model="claude-haiku-4-5")

    assert out == "stripped ok"
    child_env = captured_run["env"]
    assert child_env is not None, "expected an explicit (stripped) child env"
    assert "ANTHROPIC_API_KEY" not in child_env
    assert "CLAUDE_API_KEY" not in child_env
    # The parent process environment must be untouched.
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-ant-metered"
    assert os.environ["CLAUDE_API_KEY"] == "sk-ant-legacy"


def test_claude_cli_runs_from_neutral_cwd(captured_run):
    """The CLI must not run from this repo (it would act on it, not generate)."""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    cli_backends.send_prompt_cli("write a line", backend="claude-cli")

    assert captured_run["cwd"] is not None
    assert os.path.abspath(captured_run["cwd"]) != repo_root


def test_claude_cli_opt_out_inherits_parent_env(monkeypatch, captured_run):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-metered")

    client = cli_backends.ClaudeCliInterface(strip_provider_keys=False)
    client.generate("write a line")

    # env=None means the child inherits the parent environment untouched.
    assert captured_run["env"] is None
