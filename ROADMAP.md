# Roadmap — Prompt Injection Testing

_Status: active · updated 2026-05-30_

A multi-detector safety evaluator that runs several prompt-injection detection
strategies side by side and compares their effectiveness. Python. Grew out of the
`ScrambleGate` experiment, which is included here as one pluggable detector.

## Shipped

- [x] LLM Judge detector (safety classification, optional adversarial "suspicious" system prompts)
- [x] Regex detector (7 injection categories: override, role-play, prompt extraction, delimiter, credential exfil, tool abuse, social engineering)
- [x] BERT detector (local DeBERTa; classification + cosine-similarity modes, no API)
- [x] Weak-model detector (cheap LLM pre-filter, no tool access to avoid execution risk)
- [x] ScrambleGate detector (normalization + windowed scrambling/masking + multi-layer detection)
- [x] Multi-detector framework (parallel runs, comparison tables, per-detector metrics, disagreement analysis)
- [x] CLI backends (Claude Code / Gemini / OpenAI Codex CLIs instead of API keys)
- [x] Prompt-expansion pipeline (standard / minimal / disabled modes)
- [x] Flexible I/O (.txt or JSONL in; Markdown / CSV / JSONL / debug out)
- [x] YAML config + CLI argument overrides
- [x] Tkinter GUI wrapper (mode selection)
- [x] Agent Dojo 27-prompt benchmark findings (expansion degrades, adversarial prompts improve detection)

## Next

- [ ] Expand the evaluation dataset beyond the 27 Agent Dojo prompts
- [ ] Add more model backends (additional Claude / Gemini, o1/o3-class models)
- [ ] Per-detector latency & cost profiling

## Backlog

- [ ] Detector tuning (ScrambleGate window/stride, new scrambling modes)
- [ ] Test detectors against production / real-world attack datasets
- [ ] Adaptive-adversary robustness evaluation
