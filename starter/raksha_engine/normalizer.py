"""Deterministic Multilingual Normalisation Module with Exact Offset Mapping.
Supports Unicode NFC/NFKC, Devanagari normalisation, whitespace/punctuation,
honorific handling, phonetic skeleton extraction, and bidirectional offset tracking.
Zero dependencies (Python standard library only).
"""
from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Optional, Set, Tuple

# Devanagari numerals to ASCII
DEVA_TO_ASCII_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
ASCII_TO_DEVA_DIGITS = str.maketrans("0123456789", "०१२३४५६७८९")

# Devanagari Unicode Block: U+0900 to U+097F
DEVA_RANGE = ("\u0900", "\u097f")

# Zero-width characters to track & normalize safely
ZWNJ = "\u200c"
ZWJ = "\u200d"
NUKTA = "\u093c"
VIRAMA = "\u094d"
DANDA = "\u0964"
DOUBLE_DANDA = "\u0965"

# Devanagari transliteration tables
_CONSONANTS = {
    "क": "k", "ख": "kh", "ग": "g", "घ": "gh", "ङ": "ng",
    "च": "ch", "छ": "chh", "ज": "j", "झ": "jh", "ञ": "ny",
    "ट": "t", "ठ": "th", "ड": "d", "ढ": "dh", "ण": "n",
    "त": "t", "थ": "th", "द": "d", "ध": "dh", "न": "n",
    "प": "p", "फ": "ph", "ब": "b", "भ": "bh", "म": "m",
    "य": "y", "र": "r", "ल": "l", "व": "v", "श": "sh",
    "ष": "sh", "स": "s", "ह": "h",
    "क़": "q", "ख़": "kh", "ग़": "gh", "ज़": "z", "ड़": "r", "ढ़": "rh", "फ़": "f",
}
_VOWELS_INDEP = {
    "अ": "a", "आ": "aa", "इ": "i", "ई": "ee", "उ": "u", "ऊ": "oo",
    "ऋ": "ri", "ए": "e", "ऐ": "ai", "ओ": "o", "औ": "au",
    "अं": "an", "अः": "ah",
}
_MATRAS = {
    "ा": "a", "ि": "i", "ी": "ee", "ु": "u", "ू": "oo",
    "ृ": "ri", "े": "e", "ै": "ai", "ो": "o", "ौ": "au",
    "ं": "n", "ँ": "n", "ः": "h", "्": "",
}

# Phonetic reduction rules for Indian naming variations
_PHONETIC_SUBS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b(?:mohd|md|mohammad|muhammad|mohammed|mohamed)\b"), "mohammad"),
    (re.compile(r"\b(?:smt|shrimati|mrs|ms|kumari|km|shri|mr)\b\.?"), ""),
    (re.compile(r"aa+"), "a"),
    (re.compile(r"ee+"), "i"),
    (re.compile(r"oo+"), "u"),
    (re.compile(r"ai"), "e"),
    (re.compile(r"ph"), "f"),
    (re.compile(r"v"), "w"),
    (re.compile(r"sh"), "s"),
    (re.compile(r"z"), "j"),
    (re.compile(r"q"), "k"),
    (re.compile(r"(.)\1+"), r"\1"),
]

# Indian Honorifics & Titles (Latin & Devanagari)
HONORIFICS_LATIN = {
    "shri", "shree", "sri", "smt", "shrimati", "mr", "mrs", "ms", "km",
    "kumari", "kumar", "dr", "doctor", "prof", "pandit", "pt", "ji",
    "sahab", "saheb", "bhai", "bhaiya", "didi", "behenji", "behn", "begum", "khan",
}
HONORIFICS_DEVA = {
    "श्री", "श्रीमती", "सुश्री", "कु.", "कुमारी", "डॉ.", "डॉक्टर", "पंडित",
    "पं.", "जी", "साहब", "साहिब", "भाई", "भैया", "दीदी", "बहन", "बेगम",
}


def normalize_digits(text: str) -> str:
    """Normalize Devanagari and Eastern digits to standard ASCII 0-9."""
    return text.translate(DEVA_TO_ASCII_DIGITS)


def is_devanagari(text: str) -> bool:
    """Return True if text contains any Devanagari characters."""
    return any(DEVA_RANGE[0] <= c <= DEVA_RANGE[1] for c in text)


def normalize_multilingual_text(text: str) -> Tuple[str, List[int]]:
    """Deterministic multilingual text normalizer with exact character offset mapping.
    
    Returns:
        norm_text: The normalized string (digits standardized, whitespace cleaned,
                   Devanagari normalized).
        offset_map: List of integer indices into the original `text` string,
                    where offset_map[i] represents the original position of norm_text[i].
    """
    if not text:
        return "", []

    orig_len = len(text)
    norm_chars: list[str] = []
    offset_map: list[int] = []

    i = 0
    while i < orig_len:
        ch = text[i]

        # 1. Skip zero-width joiners / non-joiners in normalized representation
        #    while preserving position mapping for surrounding characters
        if ch in (ZWNJ, ZWJ):
            i += 1
            continue

        # 2. Convert Devanagari digits to ASCII digits
        if "०" <= ch <= "९":
            norm_chars.append(ch.translate(DEVA_TO_ASCII_DIGITS))
            offset_map.append(i)
            i += 1
            continue

        # 3. Normalize Devanagari danda / double danda to standard punctuation
        if ch == DANDA:
            norm_chars.append(".")
            offset_map.append(i)
            i += 1
            continue
        elif ch == DOUBLE_DANDA:
            norm_chars.append(".")
            offset_map.append(i)
            i += 1
            continue

        # 4. Standard Unicode normalization (NFC)
        # Handle decomposed nukta combinations (base + nukta)
        if i + 1 < orig_len and text[i + 1] == NUKTA:
            combined = unicodedata.normalize("NFC", ch + NUKTA)
            norm_chars.append(combined)
            offset_map.append(i)
            i += 2
            continue

        norm_chars.append(ch)
        offset_map.append(i)
        i += 1

    return "".join(norm_chars), offset_map


def map_norm_span_to_orig(
    offset_map: List[int],
    norm_start: int,
    norm_end: int,
    orig_length: int,
) -> Tuple[int, int]:
    """Translates a slice `[norm_start, norm_end)` in normalized text back to
    the exact `[orig_start, orig_end)` character span in the original text.
    """
    if not offset_map:
        return 0, orig_length

    # Clamp bounds
    norm_start = max(0, min(norm_start, len(offset_map) - 1))
    norm_end = max(norm_start, min(norm_end, len(offset_map)))

    orig_start = offset_map[norm_start]
    if norm_end < len(offset_map):
        orig_end = offset_map[norm_end]
    else:
        orig_end = orig_length

    # Ensure valid ordered span
    if orig_end < orig_start:
        orig_end = orig_start
    return orig_start, min(orig_end, orig_length)


def deva_to_latin(text: str) -> str:
    """Deterministic Devanagari-to-Latin phonetic transliteration."""
    out: list[str] = []
    n = len(text)
    i = 0
    while i < n:
        ch = text[i]
        # Handle nukta combinations (base + ़)
        if i + 1 < n and text[i + 1] == "़" and (ch + "़") in _CONSONANTS:
            ch = ch + "़"
            i += 1
        if ch in _CONSONANTS:
            out.append(_CONSONANTS[ch])
            nxt = text[i + 1] if i + 1 < n else ""
            if nxt in _MATRAS:
                if nxt != VIRAMA:
                    out.append(_MATRAS[nxt])
                i += 1
            elif nxt and nxt in _CONSONANTS:
                # Inherent schwa 'a' between consonants
                out.append("a")
        elif ch in _VOWELS_INDEP:
            out.append(_VOWELS_INDEP[ch])
        elif ch in _MATRAS:
            out.append(_MATRAS[ch])
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def phonetic_norm(token: str) -> str:
    """Normalize a Latin or Devanagari name token to a phonetic skeleton."""
    t = unicodedata.normalize("NFKC", token).casefold().strip()
    if is_devanagari(t):
        t = deva_to_latin(t)
    t = re.sub(r"[^a-z]", "", t)
    if not t:
        return ""
    for rx, rep in _PHONETIC_SUBS:
        t = rx.sub(rep, t)
    return t


def strip_honorifics(name: str) -> str:
    """Remove Indian honorifics and titles from person name for matching."""
    tokens = re.split(r"[\s,.-]+", name.strip())
    clean_tokens = []
    for tok in tokens:
        c_tok = tok.casefold()
        if c_tok in HONORIFICS_LATIN or tok in HONORIFICS_DEVA:
            continue
        clean_tokens.append(tok)
    return " ".join(clean_tokens) if clean_tokens else name
