"""Agent Dojo integration for ScrambleGate.

Provides SGInputGate and SGToolDetector for use with the agentdojo benchmark.
This module is optional - agentdojo must be installed separately.

Usage:
    python -m detectors.scramblegate.runner [scramble_mode]
"""

from __future__ import annotations
import os
import sys

from detectors.scramblegate.gate import gate_prompt, baseline_llm_check, GateConfig, DEFAULT_POLICY


class SGInputGate:
    """Agent Dojo pipeline element that gates initial queries with ScrambleGate."""

    def __init__(self, llm_model: str = None, scramble_mode: str = "pure_scrambling"):
        self.llm_model = llm_model
        self.scramble_mode = scramble_mode

    def query(self, query, runtime, env, messages, extra_args):
        from agentdojo.agent_pipeline import AbortAgentError

        message_texts = []
        for m in messages[-6:]:
            if hasattr(m, 'content'):
                message_texts.append(m.content)
            elif isinstance(m, dict) and 'content' in m:
                message_texts.append(m['content'])

        text = "\n\n".join([query] + message_texts)
        verdict, info = gate_prompt(
            text, DEFAULT_POLICY,
            GateConfig(rng_seed=42, scramble_mode=self.scramble_mode),
            llm_model=self.llm_model,
        )

        if verdict == "BLOCK":
            raise AbortAgentError(f"ScrambleGate blocked initial prompt: {info}")

        return query, runtime, env, messages, extra_args


class SGToolDetector:
    """Agent Dojo tool output detector using ScrambleGate."""

    def __init__(self, llm_model: str = None, raise_on_injection: bool = True,
                 scramble_mode: str = "pure_scrambling"):
        self.llm_model = llm_model
        self.raise_on_injection = raise_on_injection
        self.scramble_mode = scramble_mode

    def detect(self, tool_output: str):
        from agentdojo.agent_pipeline import AbortAgentError

        verdict, info = gate_prompt(
            tool_output, DEFAULT_POLICY,
            GateConfig(rng_seed=42, scramble_mode=self.scramble_mode),
            llm_model=self.llm_model,
        )
        is_injection = verdict == "BLOCK"
        confidence = float(info.get("max_risk", 0.0))

        if is_injection and self.raise_on_injection:
            raise AbortAgentError(f"ScrambleGate blocked tool output: {info}")

        return (is_injection, confidence)


if __name__ == "__main__":
    scramble_mode = sys.argv[1] if len(sys.argv) > 1 else "pure_scrambling"
    print(f"ScrambleGate Agent Dojo runner - mode: {scramble_mode}")
    print("This runner requires agentdojo to be installed.")
    print("See the original ScrambleGate project for the full runner implementation.")
