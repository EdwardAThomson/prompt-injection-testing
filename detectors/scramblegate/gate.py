"""Gate orchestration: the main gate_prompt() entry point."""

from __future__ import annotations
import random
from dataclasses import dataclass
from typing import List, Dict, Tuple

from detectors.scramblegate.core import (
    normalize, try_deobfuscate, tokenize_words,
    make_windows, prioritize_windows, Coverage,
)
from detectors.scramblegate.scrambler import scramble_views
from detectors.scramblegate.rules import rule_heuristics, structure_score, ml_classifier_score
from detectors.scramblegate.llm_probe import llm_probe_score_batch, aggregate


# ── Configuration ─────────────────────────────────────────────────────

@dataclass
class GateConfig:
    window_tokens: int = 800
    stride_tokens: int = 400
    views_per_window: int = 5
    num_views: int = None
    coverage_threshold: float = 0.85
    max_uncovered_gap: int = 600
    risk_threshold: float = 0.75
    random_fraction: float = 0.5
    scramble_mask_rate: float = 0.15
    rng_seed: int | None = None
    scramble_mode: str = "probabilistic"


@dataclass
class Policy:
    deny_phrases: List[str]
    tool_keywords: List[str]
    url_like: bool = True
    secret_keywords: List[str] = None


DEFAULT_POLICY = Policy(
    deny_phrases=[
        r"\bignore (all )?(previous|prior) (instructions|rules)\b",
        r"\boverride\b", r"\bdisregard\b",
        r"\bextract (the )?(system|developer) prompt\b",
        r"\breveal (secrets?|api keys?|credentials?)\b",
        r"\bimpersonate\b", r"\bprompt injection\b",
        r"\bact as (?:root|admin|developer|system)\b",
    ],
    tool_keywords=[
        "fs.readFile", "open(", "os.system", "subprocess",
        "curl", "POST /", "DELETE /", "payment", "transfer",
        "ssh", "scp", "DROP TABLE", "SELECT * FROM", "rm -rf",
    ],
    secret_keywords=["API_KEY", "SECRET", "TOKEN", "PASSWORD"],
)


# ── Gate orchestration ────────────────────────────────────────────────

def gate_prompt(
    raw_text: str,
    policy: Policy = DEFAULT_POLICY,
    cfg: GateConfig = GateConfig(),
    llm_model: str = None,
) -> Tuple[str, Dict]:
    """Run the full ScrambleGate pipeline on a prompt.

    Args:
        raw_text: The raw user prompt.
        policy: Detection policy (deny phrases, tool keywords, etc.).
        cfg: Gate configuration.
        llm_model: Model name for LLM probe (None to skip LLM probe).

    Returns:
        Tuple of (verdict, details) where verdict is "BLOCK", "ALLOW", or "ESCALATE".
    """
    rng = random.Random(cfg.rng_seed or random.getrandbits(64))

    text = normalize(raw_text)
    text = try_deobfuscate(text)
    tokens = tokenize_words(text)

    spans = make_windows(tokens, cfg.window_tokens, cfg.stride_tokens)
    order = prioritize_windows(tokens, spans, cfg, seed=rng.randrange(1 << 30))
    cov = Coverage(tokens, ngram=5)

    details = {
        "windows_checked": 0,
        "max_risk": 0.0,
        "coverage": 0.0,
        "blocked_on": None,
        "scrambled_views": [],
    }

    for span in order:
        start, end = span
        views = scramble_views(tokens, span, cfg.views_per_window, cfg, seed=rng.randrange(1 << 30))

        view_frags = [" ".join(vtok) for vtok in views]
        details["scrambled_views"].extend(view_frags[:10])  # keep first 10 for debug

        # Score non-LLM detectors per view
        max_non_llm_risk = 0.0
        for frag in view_frags:
            non_llm_risk = aggregate(
                rule_heuristics(frag, policy),
                structure_score(frag),
                ml_classifier_score(frag),
            )
            max_non_llm_risk = max(max_non_llm_risk, non_llm_risk)

        # LLM probe (optional)
        llm_risk = 0.0
        if llm_model:
            llm_risk, llm_prompt = llm_probe_score_batch(view_frags, model=llm_model)
            details["llm_system_prompt"] = llm_prompt

        r = aggregate(max_non_llm_risk, llm_risk)
        details["max_risk"] = max(details["max_risk"], r)

        if r >= cfg.risk_threshold:
            details["windows_checked"] += 1
            details["blocked_on"] = {"span": span, "risk": r}
            details["coverage"] = cov.percent()
            return "BLOCK", details

        cov.mark_span(start, end)
        details["windows_checked"] += 1

    details["coverage"] = cov.percent()
    if details["coverage"] < cfg.coverage_threshold or cov.max_gap() > cfg.max_uncovered_gap:
        return "ESCALATE", details

    return "ALLOW", details


def baseline_llm_check(raw_text: str, llm_model: str = None) -> Tuple[str, Dict]:
    """Test raw LLM detection without ScrambleGate preprocessing."""
    if not llm_model:
        return "ALLOW", {"max_risk": 0.0, "method": "baseline_no_llm"}

    try:
        risk, system_prompt = llm_probe_score_batch([raw_text], model=llm_model)
        verdict = "BLOCK" if risk >= 0.75 else "ALLOW"
        return verdict, {"max_risk": risk, "method": "baseline_llm", "llm_system_prompt": system_prompt}
    except Exception as e:
        print(f"Baseline LLM check failed: {e}")
        return "ALLOW", {"max_risk": 0.0, "method": "baseline_error"}
