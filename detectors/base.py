"""Base detector interface for prompt injection detection."""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class DetectorResult:
    """Universal result from any detector.

    Maps to SafetyJudgement for backward-compatible reporting.
    """
    label: str                           # "safe" | "unsafe" | "escalate"
    score: float                         # 0.0 (unsafe) to 1.0 (safe)
    detector_name: str
    feedback: Optional[str] = None
    raw_response: Optional[str] = None
    latency_ms: int = 0
    parse_error: bool = False
    details: Dict[str, Any] = field(default_factory=dict)

    def to_judgement_dict(self) -> Dict[str, Any]:
        """Convert to SafetyJudgement-compatible dict for existing report code."""
        result = {"label": self.label, "score": self.score}
        if self.parse_error:
            result["parse_error"] = True
        if self.feedback:
            result["feedback"] = self.feedback
        return result


class BaseDetector(ABC):
    """Abstract base class for all prompt injection detectors."""

    name: str = "base"
    requires_api: bool = False
    description: str = ""

    @abstractmethod
    def detect(self, prompt_text: str) -> DetectorResult:
        """Analyze a prompt and return a detection result."""
        ...

    def detect_timed(self, prompt_text: str) -> DetectorResult:
        """Wrapper that adds latency timing."""
        start = time.time()
        result = self.detect(prompt_text)
        result.latency_ms = int((time.time() - start) * 1000)
        return result
