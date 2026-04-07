"""Regex-based prompt injection detector.

No API calls, no external dependencies. Pattern-matches against known
injection techniques and scores prompts by weighted severity.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from detectors.base import BaseDetector, DetectorResult


@dataclass
class PatternRule:
    """A single regex pattern with severity weight and category."""
    pattern: str
    weight: float       # 0.0 - 1.0 severity
    category: str
    _compiled: re.Pattern = field(init=False, repr=False, default=None)

    def __post_init__(self):
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def search(self, text: str):
        return self._compiled.search(text)


# --- Default pattern library ---

INSTRUCTION_OVERRIDE = [
    PatternRule(r"\bignore\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|guidelines|prompts?)\b", 0.95, "instruction_override"),
    PatternRule(r"\bdisregard\s+(all\s+)?(previous|prior|above)\s+(instructions|rules|guidelines)\b", 0.95, "instruction_override"),
    PatternRule(r"\bforget\s+(all\s+)?(your|previous|prior)\s+(instructions|rules|training)\b", 0.90, "instruction_override"),
    PatternRule(r"\boverride\s+(safety|content|your)\s+(filter|policy|rules|instructions)\b", 0.90, "instruction_override"),
    PatternRule(r"\bdo\s+not\s+follow\s+(your|any|the)\s+(rules|instructions|guidelines)\b", 0.90, "instruction_override"),
    PatternRule(r"\byou\s+are\s+now\s+(free|released|unbound|unrestricted)\b", 0.85, "instruction_override"),
    PatternRule(r"\bnew\s+instructions?\s*:", 0.70, "instruction_override"),
]

ROLEPLAY_TRIGGERS = [
    PatternRule(r"\byou\s+are\s+now\s+(?:a|an|the)\b", 0.60, "roleplay"),
    PatternRule(r"\bact\s+as\s+(?:if\s+you\s+(?:are|were)|a|an|the|root|admin|developer|system)\b", 0.70, "roleplay"),
    PatternRule(r"\bpretend\s+(?:to\s+be|you\s+are)\b", 0.65, "roleplay"),
    PatternRule(r"\broleplay\s+as\b", 0.65, "roleplay"),
    PatternRule(r"\bjailbreak\b", 0.90, "roleplay"),
    PatternRule(r"\bDAN\s+mode\b", 0.90, "roleplay"),
]

SYSTEM_PROMPT_EXTRACTION = [
    PatternRule(r"\b(show|reveal|display|print|output|repeat)\s+(me\s+)?(your|the)\s+(system\s+prompt|instructions|rules|initial\s+prompt)\b", 0.90, "extraction"),
    PatternRule(r"\bwhat\s+(are|is)\s+your\s+(system\s+prompt|instructions|rules|initial\s+prompt)\b", 0.80, "extraction"),
    PatternRule(r"\b(extract|leak|dump)\s+(the\s+)?(system|developer)\s+(prompt|instructions)\b", 0.95, "extraction"),
    PatternRule(r"\breveal\s+(secrets?|api\s*keys?|credentials?|tokens?|passwords?)\b", 0.95, "extraction"),
]

DELIMITER_INJECTION = [
    PatternRule(r"\[SYSTEM\]", 0.85, "delimiter"),
    PatternRule(r"<\|im_start\|>", 0.90, "delimiter"),
    PatternRule(r"<<SYS>>", 0.90, "delimiter"),
    PatternRule(r"\[INST\]", 0.85, "delimiter"),
    PatternRule(r"<\|endoftext\|>", 0.85, "delimiter"),
    PatternRule(r"###\s*(system|instruction|human|assistant)\s*:", 0.75, "delimiter"),
    PatternRule(r"```\s*system\b", 0.75, "delimiter"),
]

CREDENTIAL_EXFIL = [
    PatternRule(r"\b(send|post|exfiltrate|upload)\s+.{0,30}(api\s*key|secret|token|password|credential)", 0.90, "credential_exfil"),
    PatternRule(r"\b(api[_\s]?key|secret[_\s]?key|access[_\s]?token)\b.{0,30}\b(to|at|via)\s+https?://", 0.95, "credential_exfil"),
]

TOOL_ABUSE = [
    PatternRule(r"\b(run|execute|eval)\s+(this\s+)?(command|code|script)\b", 0.70, "tool_abuse"),
    PatternRule(r"\brm\s+-rf\b", 0.95, "tool_abuse"),
    PatternRule(r"\bDROP\s+TABLE\b", 0.95, "tool_abuse"),
    PatternRule(r"\bSELECT\s+\*\s+FROM\b", 0.60, "tool_abuse"),
    PatternRule(r"\bos\.system\b", 0.85, "tool_abuse"),
    PatternRule(r"\bsubprocess\.(call|run|Popen)\b", 0.85, "tool_abuse"),
    PatternRule(r"\bfs\.readFile\b", 0.80, "tool_abuse"),
    PatternRule(r"\bcurl\s+.{0,50}https?://", 0.65, "tool_abuse"),
    PatternRule(r"\b(POST|DELETE|PUT)\s+/", 0.60, "tool_abuse"),
]

SOCIAL_ENGINEERING = [
    PatternRule(r"\b(this\s+is\s+)?(an?\s+)?(emergency|urgent|critical)\b.{0,30}\b(need|must|require)\b", 0.55, "social_engineering"),
    PatternRule(r"\bI\s+am\s+(the\s+)?(admin|developer|owner|CEO|CTO)\b", 0.65, "social_engineering"),
    PatternRule(r"\bauthorized\s+(to|by)\b.{0,20}\b(access|override|bypass)\b", 0.70, "social_engineering"),
]

DEFAULT_PATTERNS = {
    "instruction_override": INSTRUCTION_OVERRIDE,
    "roleplay": ROLEPLAY_TRIGGERS,
    "extraction": SYSTEM_PROMPT_EXTRACTION,
    "delimiter": DELIMITER_INJECTION,
    "credential_exfil": CREDENTIAL_EXFIL,
    "tool_abuse": TOOL_ABUSE,
    "social_engineering": SOCIAL_ENGINEERING,
}


class RegexDetector(BaseDetector):
    """Pattern-matching detector for known injection techniques."""

    name = "regex"
    requires_api = False
    description = "Regex pattern matching for known injection patterns"

    def __init__(self, patterns: Optional[Dict[str, List[PatternRule]]] = None,
                 risk_threshold: float = 0.5, **kwargs):
        self.patterns = patterns or DEFAULT_PATTERNS
        self.risk_threshold = risk_threshold

    def detect(self, prompt_text: str) -> DetectorResult:
        text = prompt_text.strip()
        matches = []
        max_weight = 0.0

        for category, rules in self.patterns.items():
            for rule in rules:
                match = rule.search(text)
                if match:
                    matches.append({
                        "category": category,
                        "pattern": rule.pattern,
                        "weight": rule.weight,
                        "matched_text": match.group(),
                    })
                    if rule.weight > max_weight:
                        max_weight = rule.weight

        # Score: combine max severity with breadth (number of categories hit)
        categories_hit = len(set(m["category"] for m in matches))
        breadth_bonus = min(categories_hit * 0.05, 0.15)  # up to 0.15 bonus
        risk_score = min(max_weight + breadth_bonus, 1.0) if matches else 0.0
        safe_score = 1.0 - risk_score

        label = "unsafe" if risk_score >= self.risk_threshold else "safe"

        feedback_parts = []
        if matches:
            for m in matches:
                feedback_parts.append(
                    f"[{m['category']}] matched: \"{m['matched_text']}\" (severity: {m['weight']:.2f})"
                )

        return DetectorResult(
            label=label,
            score=safe_score,
            detector_name=self.name,
            feedback="\n".join(feedback_parts) if feedback_parts else None,
            details={
                "matches": matches,
                "risk_score": risk_score,
                "categories_hit": categories_hit,
                "total_matches": len(matches),
            },
        )
