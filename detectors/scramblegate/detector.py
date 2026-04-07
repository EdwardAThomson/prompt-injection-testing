"""ScrambleGate adapter for the BaseDetector interface."""

from detectors.base import BaseDetector, DetectorResult
from detectors.scramblegate.gate import gate_prompt, GateConfig, Policy, DEFAULT_POLICY


class ScrambleGateDetector(BaseDetector):
    """ScrambleGate multi-layer detection with stochastic scrambling."""

    name = "scramblegate"
    requires_api = True
    description = "ScrambleGate stochastic gating (rules + optional LLM probe)"

    def __init__(
        self,
        scramble_mode: str = "probabilistic",
        risk_threshold: float = 0.75,
        window_tokens: int = 800,
        stride_tokens: int = 400,
        views_per_window: int = 5,
        use_llm_probe: bool = True,
        llm_model: str = None,
        **kwargs,
    ):
        self.gate_config = GateConfig(
            window_tokens=window_tokens,
            stride_tokens=stride_tokens,
            views_per_window=views_per_window,
            risk_threshold=risk_threshold,
            scramble_mode=scramble_mode,
        )
        self.policy = DEFAULT_POLICY
        if use_llm_probe:
            if llm_model is None:
                from config import DEFAULT_MODEL
                llm_model = DEFAULT_MODEL
            self.llm_model = llm_model
        else:
            self.llm_model = None

        if not use_llm_probe:
            self.requires_api = False

    def detect(self, prompt_text: str) -> DetectorResult:
        verdict, info = gate_prompt(
            prompt_text,
            policy=self.policy,
            cfg=self.gate_config,
            llm_model=self.llm_model,
        )

        # Map verdict to label and invert risk -> safety score
        label_map = {"BLOCK": "unsafe", "ALLOW": "safe", "ESCALATE": "unsafe"}
        label = label_map.get(verdict, "unsafe")

        max_risk = info.get("max_risk", 0.0)
        # ESCALATE gets a moderate safety score (not fully unsafe)
        if verdict == "ESCALATE":
            safe_score = 0.4
        else:
            safe_score = 1.0 - max_risk

        return DetectorResult(
            label=label,
            score=safe_score,
            detector_name=self.name,
            feedback=f"ScrambleGate verdict: {verdict}",
            details={
                "verdict": verdict,
                "windows_checked": info.get("windows_checked", 0),
                "coverage": info.get("coverage", 0.0),
                "max_risk": max_risk,
                "blocked_on": info.get("blocked_on"),
                "scramble_mode": self.gate_config.scramble_mode,
            },
        )
