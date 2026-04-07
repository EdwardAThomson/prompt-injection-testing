"""Rule-based heuristics and structural anomaly detection."""

from __future__ import annotations
import re
from typing import List

from detectors.scramblegate.core import B64_RE, SALIENT_RE


def rule_heuristics(text: str, policy) -> float:
    """Score risk based on deny phrases, tool keywords, secrets, and URLs."""
    risk = 0.0
    lower = text.lower()

    for pat in policy.deny_phrases:
        if re.search(pat, lower):
            risk = max(risk, 0.9)

    for kw in policy.tool_keywords:
        if kw.lower() in lower:
            risk = max(risk, 0.6)

    if policy.secret_keywords:
        for sk in policy.secret_keywords:
            if sk.lower() in lower:
                risk = max(risk, 0.8)

    if policy.url_like and re.search(r"https?://|[\w-]+\.[a-z]{2,}", lower):
        risk = max(risk, 0.4)

    return min(risk, 1.0)


def structure_score(text: str) -> float:
    """Flag big encoded blobs and structural anomalies."""
    risk = 0.0
    if re.search(B64_RE, text):
        risk = max(risk, 0.5)
    if re.search(r"([^\w\s])\1{6,}", text):
        risk = max(risk, 0.4)
    if re.search(r"(?:\[MASK\]\s*){20,}", text):
        risk = max(risk, 0.3)
    return risk


def ml_classifier_score(text: str) -> float:
    """Stub ML classifier. Counts salient keyword hits as a naive proxy."""
    hits = len(SALIENT_RE.findall(text))
    return min(0.1 * hits, 0.7)
