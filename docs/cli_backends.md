# CLI Backends

CLI backends let you send prompts to AI models via locally installed command-line tools instead of API keys. This is useful for:

- **Zero API cost** - uses your existing CLI subscriptions
- **No API key management** - no environment variables needed
- **Safe pre-filtering** - CLI tools don't expose tool-calling, making them ideal for the `weak_model` detector use case

## Supported CLI Tools

### Claude Code CLI

| Model ID | CLI Model | Notes |
|----------|-----------|-------|
| `claude-cli` | `claude-opus-4-6` | Default (most capable) |
| `claude-cli-sonnet` | `claude-sonnet-4-6` | Balanced speed/quality |
| `claude-cli-haiku` | `claude-haiku-4-5` | Fast and cheap |

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

**All available Gemini CLI models** (v0.36.0):
`gemini-3-flash-preview`, `gemini-3-pro-preview`, `gemini-3.1-pro-preview`,
`gemini-3.1-flash-lite-preview`, `gemini-2.5-pro`, `gemini-2.5-flash`,
`gemini-2.5-flash-lite`

### Codex CLI (OpenAI)

| Model ID | CLI Model | Notes |
|----------|-----------|-------|
| `codex` | `gpt-5.4` | Default (most capable) |
| `codex-mini` | `gpt-5.4-mini` | Smaller/cheaper |
| `codex-5.3` | `gpt-5.3-codex` | Previous gen codex |
| `codex-5.2` | `gpt-5.2-codex` | Older codex model |

**Install:** `npm install -g @openai/codex` (requires >= 0.118.0)

**Invocation:** `codex exec -m <model> --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check <prompt>`

**All models found in Codex CLI** (v0.118.0):
`gpt-5.4`, `gpt-5.4-mini`, `gpt-5.4-pro`, `gpt-5.3-codex`, `gpt-5.2-codex`,
`gpt-5.2`, `gpt-5.1-codex`, `gpt-5.1-codex-max`, `gpt-5.1-codex-mini`,
`gpt-5-codex`, `gpt-5-codex-mini`, `gpt-5-mini`, `gpt-5-nano`,
`gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`

**Note:** o3/o4-mini are NOT supported with ChatGPT accounts.

## Checking Availability

```python
from cli_backends import check_cli_availability
print(check_cli_availability())
# {'claude-cli': True, 'gemini-cli': True, 'codex': True}
```

Or from the command line:
```bash
python -c "from cli_backends import check_cli_availability; print(check_cli_availability())"
```

## Usage Examples

### Direct use via ai_helper
```python
from ai_helper import send_prompt

# Claude (opus by default)
response = send_prompt("Classify this prompt for safety", model="claude-cli")

# Claude haiku (fast/cheap)
response = send_prompt("Classify this prompt for safety", model="claude-cli-haiku")

# Gemini flash
response = send_prompt("Classify this prompt for safety", model="gemini-cli")

# GPT-5.4 via Codex
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
