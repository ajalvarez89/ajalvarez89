"""Lightweight sentiment scorer.

This intentionally avoids loading FinBERT / torch in news_collector to keep
its container small. Scoring is delegated to ml_service in Phase 5+ via
HTTP. As a fallback (and for the offline path), we ship a tiny VADER-style
lexicon that works well enough on financial headlines.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


_POS = {
    "surge", "surges", "soar", "soars", "soared", "rally", "rallies", "rallied",
    "bull", "bullish", "bull-run", "breakout", "outperforms", "outperform",
    "approval", "approve", "approved", "boost", "gain", "gains", "growth",
    "win", "wins", "win-win", "positive", "record", "all-time-high", "ath",
    "buy", "buying", "rebound", "recovers", "recovery",
}

_NEG = {
    "crash", "crashes", "plunge", "plunges", "plunged", "tumble", "tumbles",
    "bear", "bearish", "selloff", "sell-off", "dump", "dumps", "dumped",
    "ban", "banned", "halt", "halted", "hack", "hacked", "exploit", "exploits",
    "lawsuit", "subpoena", "investigation", "fraud", "ponzi", "rug", "rugpull",
    "scam", "loss", "losses", "fall", "falls", "fell", "drop", "drops", "down",
    "warning", "risk", "panic", "freeze", "frozen", "delisted", "decline",
}


@dataclass
class SentimentScore:
    label: str  # "positive" | "neutral" | "negative"
    score: float  # range [-1, 1]
    pos_hits: int
    neg_hits: int


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z\-]+")


def score_text(text: str) -> SentimentScore:
    if not text:
        return SentimentScore("neutral", 0.0, 0, 0)
    tokens = [t.lower() for t in _TOKEN_RE.findall(text)]
    pos = sum(1 for t in tokens if t in _POS)
    neg = sum(1 for t in tokens if t in _NEG)

    total = pos + neg
    if total == 0:
        return SentimentScore("neutral", 0.0, 0, 0)
    raw = (pos - neg) / total  # in [-1, 1]
    if raw > 0.2:
        label = "positive"
    elif raw < -0.2:
        label = "negative"
    else:
        label = "neutral"
    return SentimentScore(label=label, score=round(raw, 3), pos_hits=pos, neg_hits=neg)
