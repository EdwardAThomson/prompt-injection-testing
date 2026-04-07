"""Normalization, deobfuscation, tokenization, windowing, coverage, and saliency."""

from __future__ import annotations
import base64, binascii, random, re, unicodedata
from dataclasses import dataclass
from typing import List, Tuple, Set


# ── Normalization / Deobfuscation ─────────────────────────────────────

ZW_RE = re.compile(r"[\u200B-\u200F\u202A-\u202E\u2060\u2066-\u2069]")
HOMOGLYPHS = {
    "\u237a": "\u03b1", "\uff21": "A", "\u0412": "B", "\u0421": "C",
    "\u0395": "E", "\u0397": "H", "\u0406": "I", "\u0408": "J",
    "\u039a": "K", "\u039c": "M", "\u039d": "N", "\u041e": "O",
    "\u0420": "P", "\u03a4": "T", "\u0425": "X", "\u03a5": "Y",
    "\u0430": "a", "\u0435": "e", "\u043e": "o", "\u0440": "p",
    "\u0441": "s", "\u0443": "y", "\u0445": "x",
}


def normalize(text: str) -> str:
    """Strip zero-width chars, replace homoglyphs, NFKC normalize, collapse whitespace."""
    text = ZW_RE.sub("", text)
    text = "".join(HOMOGLYPHS.get(ch, ch) for ch in text)
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


B64_RE = re.compile(r"(?:[A-Za-z0-9+/]{20,}={0,2})")


def try_deobfuscate(text: str, max_expansions: int = 3) -> str:
    """Heuristic base64/hex/URL decode where plausible."""
    out = text
    for _ in range(max_expansions):
        changed = False

        # base64
        for m in list(B64_RE.finditer(out)):
            blob = m.group(0)
            try:
                dec = base64.b64decode(blob, validate=True)
                if 16 <= len(dec) <= 4000 and is_mostly_text(dec):
                    out = out.replace(blob, dec.decode("utf-8", errors="ignore"))
                    changed = True
            except Exception:
                pass

        # hex
        for m in re.finditer(r"\b([0-9a-fA-F]{2}){16,}\b", out):
            blob = m.group(0)
            try:
                dec = binascii.unhexlify(blob)
                if 16 <= len(dec) <= 4000 and is_mostly_text(dec):
                    out = out.replace(blob, dec.decode("utf-8", errors="ignore"))
                    changed = True
            except Exception:
                pass

        # url decode (%xx)
        if re.search(r"%[0-9A-Fa-f]{2}", out):
            try:
                new = binascii.a2b_qp(out.replace('%', '=')).decode('utf-8', 'ignore')
            except Exception:
                new = out
            if new != out:
                out = new
                changed = True

        if not changed:
            break
    return out


def is_mostly_text(b: bytes) -> bool:
    if not b:
        return False
    textish = sum((32 <= c <= 126) or c in (9, 10, 13) for c in b)
    return textish / max(1, len(b)) > 0.8


# ── Tokenization / Windows / Coverage ─────────────────────────────────

def tokenize_words(text: str) -> List[str]:
    """Quick proxy for tokens; split into words and punctuation."""
    return re.findall(r"\w+|[^\w\s]", text, re.UNICODE)


def make_windows(tokens: List[str], win: int, stride: int) -> List[Tuple[int, int]]:
    """Create overlapping windows over token list, always including head/tail hotspots."""
    spans = []
    i = 0
    n = len(tokens)
    while i < n:
        spans.append((i, min(i + win, n)))
        if i + win >= n:
            break
        i += stride
    # Always scan first/last N deterministically
    N = min(win, 400)
    head = (0, min(N, n))
    tail = (max(0, n - N), n)
    if head not in spans:
        spans.insert(0, head)
    if tail not in spans:
        spans.append(tail)
    # dedupe while keeping order
    seen = set()
    uniq = []
    for s in spans:
        if s not in seen:
            uniq.append(s)
            seen.add(s)
    return uniq


class Coverage:
    """Track n-gram coverage across inspected windows."""

    def __init__(self, tokens: List[str], ngram: int = 5):
        self.ngram = ngram
        self.total_ngrams = max(0, len(tokens) - ngram + 1)
        self.seen: Set[int] = set()
        self.tokens = tokens

    def mark_span(self, start: int, end: int):
        for i in range(start, max(start, end - self.ngram + 1)):
            self.seen.add(i)

    def percent(self) -> float:
        if self.total_ngrams == 0:
            return 1.0
        return len(self.seen) / self.total_ngrams

    def max_gap(self) -> int:
        covered = sorted(list(self.seen))
        if not covered:
            return len(self.tokens)
        gaps = []
        last = covered[0]
        for idx in covered[1:]:
            if idx == last + 1:
                last = idx
            else:
                gaps.append(idx - last)
                last = idx
        return max(gaps or [0])


# ── Saliency & Sampling ──────────────────────────────────────────────

SALIENT_RE = re.compile(
    r"(ignore|override|disregard|reveal|system prompt|developer|"
    r"secrets?|api key|token|password|act as|tool|function|exec|curl|POST|DELETE|rm -rf)",
    re.IGNORECASE,
)


def window_saliency(tokens: List[str], span: Tuple[int, int]) -> int:
    """Count salient keyword hits in a window."""
    frag = "".join(tokens[span[0]:span[1]])
    return len(SALIENT_RE.findall(frag))


def prioritize_windows(
    tokens: List[str], spans: List[Tuple[int, int]], cfg, seed: int,
) -> List[Tuple[int, int]]:
    """Mix salient windows with random sampling for unpredictable ordering."""
    rng = random.Random(seed)
    scored = [(span, window_saliency(tokens, span)) for span in spans]
    salient = [s for s, sc in scored if sc > 0]
    rest = [s for s, sc in scored if sc == 0]
    rng.shuffle(salient)
    rng.shuffle(rest)
    k_sal = int(len(spans) * (1 - cfg.random_fraction))
    ordered = salient[:k_sal] + rest
    random_sample = spans[:]
    rng.shuffle(random_sample)
    mix = ordered[:len(spans) // 2] + random_sample
    # dedupe preserve order
    uniq = []
    seen = set()
    for s in mix:
        if s not in seen:
            uniq.append(s)
            seen.add(s)
    return uniq
