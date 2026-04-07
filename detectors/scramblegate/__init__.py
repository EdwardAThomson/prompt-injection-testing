"""ScrambleGate: stochastic gating defense against prompt injection.

Ported from https://github.com/EdwardAThomson/ScrambleGate
"""

from detectors.scramblegate.gate import gate_prompt, baseline_llm_check, GateConfig, Policy, DEFAULT_POLICY
from detectors.scramblegate.detector import ScrambleGateDetector
