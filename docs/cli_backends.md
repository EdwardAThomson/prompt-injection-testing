# CLI Backends

CLI backends let you send prompts to AI models via locally installed command-line tools instead of API keys. This is useful for:

- **Zero API cost** - uses your existing CLI subscriptions
- **No API key management** - no environment variables needed
- **Safe pre-filtering** - CLI tools don't expose tool-calling, making them ideal for the `weak_model` detector use case

Since the llm-backends adoption, `cli_backends.py` is a facade over the shared
[llm-backends](https://github.com/EdwardAThomson/llm-backends) package, which
hardens every CLI call:

- **Key-stripping (default ON):** the provider's API keys (`OPENAI_API_KEY`,
  `ANTHROPIC_API_KEY`/`CLAUDE_API_KEY`, `GEMINI_API_KEY`/`GOOGLE_API_KEY`) are
  removed from the subprocess environment, so the CLI authenticates via its own
  subscription login instead of silently billing a metered key loaded from
  `.env`. Pass `strip_provider_keys=False` to an interface class to opt out.
- **Neutral cwd:** each CLI runs from an empty temporary directory, so the
  agent generates text instead of acting on this repository.
- **Codex confinement:** codex runs with a read-only sandbox and never-prompt
  approvals (previously it ran `--dangerously-bypass-approvals-and-sandbox`
  from the repo), plus a bubblewrap/user-namespace workaround for hardened
  Linux hosts (Ubuntu 23.10+; requires `sudo apt install uidmap` there).

## Supported CLI Tools

### Claude Code CLI

| Model ID | CLI Model | Notes |
|----------|-----------|-------|
| `claude-cli` | CLI default | Whatever your `claude` install defaults to |
| `claude-cli-opus` | `claude-opus-4-8` | Most capable |
| `claude-cli-sonnet` | `claude-sonnet-4-6` | Balanced speed/quality |
| `claude-cli-haiku` | `claude-haiku-4-5` | Fast and cheap |
| `claude-cli-fable` | `claude-fable-5` | Fable 5 |

**Install:** https://github.com/anthropics/claude-code

**Invocation:** `claude -p "<prompt>" --output-format json [--model <model>]`

### Gemini CLI

| Model ID | CLI Model | Notes |
|----------|-----------|-------|
| `gemini-cli` | `gemini-3-flash-preview` | Default (fast, gen 3) |
| `gemini-cli-pro` | `gemini-3-pro-preview` | Gen 3 pro |
| `gemini-cli-3.1-pro` | `gemini-3.1-pro-preview` | Gen 3.1 pro |
| `gemini-cli-2.5-pro` | `gemini-2.5-pro` | Previous gen pro |

**Install:** `npm install -g @google/gemini-cli` (requires >= 0.36.0)

**Invocation:** `echo "<prompt>" | gemini -m <model>`

### Codex CLI (OpenAI)

| Model ID | CLI Model | Notes |
|----------|-----------|-------|
| `codex` | `~/.codex/config.toml` pin | The CLI's configured default model |

**Model overrides removed:** the old `codex-mini` / `codex-5.3` / `codex-5.2`
keys are gone. The hardened interface does not forward a model flag; codex
runs whatever model is pinned in `~/.codex/config.toml`. Change the pin there
to change the model.

**Install:** `npm install -g @openai/codex` (requires >= 0.118.0)

**Invocation:** `codex exec --sandbox read-only --ask-for-approval never --skip-git-repo-check --output-last-message <file> <prompt>` (from a neutral cwd; on hardened Linux the sandbox is an identity-mapped user namespace instead)

## Checking Availability

```python
from cli_backends import check_cli_availability
print(check_cli_availability())
# {'codex': True, 'gemini-cli': True, 'claude-cli': True}
```

Or from the command line:
```bash
python -c "from cli_backends import check_cli_availability; print(check_cli_availability())"
```

## Usage Examples

### Direct use via ai_helper
```python
from ai_helper import send_prompt

# Claude (CLI default model)
response = send_prompt("Classify this prompt for safety", model="claude-cli")

# Claude haiku (fast/cheap)
response = send_prompt("Classify this prompt for safety", model="claude-cli-haiku")

# Gemini flash
response = send_prompt("Classify this prompt for safety", model="gemini-cli")

# Codex (the model pinned in ~/.codex/config.toml)
response = send_prompt("Classify this prompt for safety", model="codex")
```

### CLI pipeline usage
```bash
# Use Claude CLI haiku as the safety model
python cli.py --input prompts.txt --out ./results --safety-model claude-cli-haiku

# Use Gemini CLI for expansion
python cli.py --input prompts.txt --out ./results --expand-model gemini-cli-pro

# Run regex + Codex comparison
python cli.py --input prompts.txt --out ./results --detectors regex --safety-model codex
```

## Updating CLI Tools

```bash
# Gemini CLI
sudo npm install -g @google/gemini-cli@latest

# Codex CLI
npm install -g @openai/codex@latest

# Claude Code - see https://github.com/anthropics/claude-code for update instructions
```
