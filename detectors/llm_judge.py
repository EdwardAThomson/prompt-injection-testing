"""LLM-based safety classifier detector. Wraps the existing SafetyJudge."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from detectors.base import BaseDetector, DetectorResult
from judge import SafetyJudge


class LLMJudgeDetector(BaseDetector):
    """Wraps the existing SafetyJudge as a BaseDetector."""

    name = "llm_judge"
    requires_api = True
    description = "LLM-based safety classifier"

    def __init__(self, model: str = None, temperature: float = 0.0,
                 max_tokens: int = 256, retry_attempts: int = 3,
                 retry_backoff: float = 2.0, stop_on_parse_error: bool = False,
                 feedback_mode: bool = False, **kwargs):
        if model is None:
            from config import DEFAULT_MODEL
            model = DEFAULT_MODEL
        self.judge = SafetyJudge(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            retry_attempts=retry_attempts,
            retry_backoff=retry_backoff,
            stop_on_parse_error=stop_on_parse_error,
            feedback_mode=feedback_mode,
        )

    def detect(self, prompt_text: str) -> DetectorResult:
        judgement = self.judge.classify(prompt_text)
        return DetectorResult(
            label=judgement.label,
            score=judgement.score,
            detector_name=self.name,
            feedback=judgement.feedback,
            raw_response=judgement.raw_response,
            latency_ms=judgement.latency_ms,
            parse_error=judgement.parse_error,
            details={
                "model": self.judge.model,
                "feedback_mode": self.judge.feedback_mode,
            },
        )
