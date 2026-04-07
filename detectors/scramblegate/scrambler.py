"""Scrambling and masking functions for generating multiple views of text windows."""

from __future__ import annotations
import random, re
from typing import List, Tuple


def scramble_views(
    tokens: List[str], span: Tuple[int, int], k: int, cfg, seed: int,
) -> List[List[str]]:
    """Generate k scrambled/masked views of a token window.

    Supports multiple modes configured via cfg.scramble_mode.
    """
    actual_k = cfg.num_views if cfg.num_views is not None else k
    rng = random.Random(seed + span[0] * 131 + span[1] * 17)
    start, end = span
    window = tokens[start:end]
    views = []

    mode = cfg.scramble_mode

    if mode == "probabilistic":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            rand_val = rng_alt.random()
            if rand_val < 0.3:
                views.append(window[:])
            elif rand_val < 0.5:
                mask_rng = random.Random(seed + i * 1000 + 100)
                views.append(mask_tokens_probabilistic(window, cfg.scramble_mask_rate, mask_rng))
            elif rand_val < 0.7:
                scramble_rng = random.Random(seed + i * 1000 + 200)
                views.append(scramble_words(window, scramble_rng))
            else:
                scramble_rng = random.Random(seed + i * 1000 + 300)
                mask_rng = random.Random(seed + i * 1000 + 400)
                scrambled = scramble_words(window, scramble_rng)
                views.append(mask_tokens_probabilistic(scrambled, cfg.scramble_mask_rate, mask_rng))

    elif mode == "broken_probabilistic":
        # Replicate the original broken algorithm that performed better
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            if rng_alt.random() < 0.3:
                views.append(window[:])
            elif rng_alt.random() < 0.5:  # chained random() calls
                mask_rng = random.Random(seed + i * 1000 + 100)
                views.append(mask_tokens_probabilistic(window, cfg.scramble_mask_rate, mask_rng))
            elif rng_alt.random() < 0.7:
                scramble_rng = random.Random(seed + i * 1000 + 200)
                views.append(scramble_words(window, scramble_rng))
            else:
                scramble_rng = random.Random(seed + i * 1000 + 300)
                mask_rng = random.Random(seed + i * 1000 + 400)
                scrambled = scramble_words(window, scramble_rng)
                views.append(mask_tokens_probabilistic(scrambled, cfg.scramble_mask_rate, mask_rng))

    elif mode == "deterministic_masking":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            if i == 0:
                views.append(scramble_words(window, rng_alt))
            elif i == 1:
                views.append(mask_tokens_deterministic(window, 0.2, rng_alt))
            elif i == 2:
                views.append(mask_tokens_deterministic(window, 0.4, rng_alt))
            elif i == 3:
                scrambled = scramble_words(window, rng_alt)
                views.append(mask_tokens_deterministic(scrambled, 0.2, rng_alt))
            else:
                scrambled = scramble_words(window, rng_alt)
                views.append(mask_tokens_deterministic(scrambled, 0.4, rng_alt))

    elif mode == "pure_scrambling":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            views.append(scramble_words(window, rng_alt))

    elif mode == "masking_only":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            rate = 0.2 if i < 2 else 0.4
            views.append(mask_tokens_deterministic(window, rate, rng_alt))

    elif mode == "clean_only":
        for i in range(actual_k):
            views.append(window[:])

    elif mode == "masking_brackets":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            views.append(mask_tokens_brackets(window, cfg.scramble_mask_rate, rng_alt))

    elif mode == "masking_redacted":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            views.append(mask_tokens_redacted(window, cfg.scramble_mask_rate, rng_alt))

    elif mode == "masking_asterisks":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            views.append(mask_tokens_asterisks(window, cfg.scramble_mask_rate, rng_alt))

    elif mode == "optimized_masking":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            rand_val = rng_alt.random()
            if rand_val < 0.25:
                views.append(window[:])
            elif rand_val < 0.70:
                mask_rng = random.Random(seed + i * 1000 + 100)
                views.append(mask_tokens_redacted(window, cfg.scramble_mask_rate, mask_rng))
            elif rand_val < 0.85:
                scramble_rng = random.Random(seed + i * 1000 + 200)
                views.append(scramble_words(window, scramble_rng))
            else:
                scramble_rng = random.Random(seed + i * 1000 + 300)
                mask_rng = random.Random(seed + i * 1000 + 400)
                scrambled = scramble_words(window, scramble_rng)
                views.append(mask_tokens_redacted(scrambled, cfg.scramble_mask_rate, mask_rng))

    elif mode == "balanced_precision":
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            rand_val = rng_alt.random()
            if rand_val < 0.40:
                views.append(window[:])
            elif rand_val < 0.65:
                mask_rng = random.Random(seed + i * 1000 + 100)
                views.append(mask_tokens_brackets(window, cfg.scramble_mask_rate, mask_rng))
            elif rand_val < 0.85:
                mask_rng = random.Random(seed + i * 1000 + 200)
                views.append(mask_tokens_probabilistic(window, cfg.scramble_mask_rate, mask_rng))
            else:
                scramble_rng = random.Random(seed + i * 1000 + 300)
                views.append(scramble_words(window, scramble_rng))

    else:
        # Default fallback to pure scrambling
        for i in range(actual_k):
            rng_alt = random.Random(seed + i * 1000)
            views.append(scramble_words(window, rng_alt))

    return views


# ── Masking functions ─────────────────────────────────────────────────

def mask_tokens_probabilistic(tok: List[str], rate: float, rng: random.Random) -> List[str]:
    """Mask tokens probabilistically with [MASK]."""
    return [("[MASK]" if re.match(r"\w", t) and rng.random() < rate else t) for t in tok]


def mask_tokens_brackets(tok: List[str], rate: float, rng: random.Random) -> List[str]:
    """Mask tokens with [] tokens."""
    return [("[]" if re.match(r"\w", t) and rng.random() < rate else t) for t in tok]


def mask_tokens_redacted(tok: List[str], rate: float, rng: random.Random) -> List[str]:
    """Mask tokens with [REDACTED] tokens."""
    return [("[REDACTED]" if re.match(r"\w", t) and rng.random() < rate else t) for t in tok]


def mask_tokens_asterisks(tok: List[str], rate: float, rng: random.Random) -> List[str]:
    """Mask tokens with *** tokens."""
    return [("***" if re.match(r"\w", t) and rng.random() < rate else t) for t in tok]


def mask_tokens_deterministic(tok: List[str], rate: float, rng: random.Random) -> List[str]:
    """Mask exactly rate% of word tokens."""
    word_indices = [i for i, t in enumerate(tok) if re.match(r"\w", t)]
    if not word_indices:
        return tok[:]
    num_to_mask = max(1, int(len(word_indices) * rate))
    indices_to_mask = set(rng.sample(word_indices, min(num_to_mask, len(word_indices))))
    return [("[MASK]" if i in indices_to_mask else t) for i, t in enumerate(tok)]


def scramble_words(tok: List[str], rng: random.Random) -> List[str]:
    """Scramble word order while preserving punctuation positions."""
    words = []
    word_positions = []
    for i, t in enumerate(tok):
        if re.match(r"\w", t):
            words.append(t)
            word_positions.append(i)
    if len(words) <= 1:
        return tok[:]
    scrambled_words = words[:]
    rng.shuffle(scrambled_words)
    out = tok[:]
    for pos, new_word in zip(word_positions, scrambled_words):
        out[pos] = new_word
    return out
