"""
Enums and normalization helpers for validating scraped table values and
creating short, filename-friendly codes.

The enums intentionally use short UPPER_SNAKE_CASE values suitable for filenames.
Normalization helpers convert human-readable scraped strings to enum values.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Tuple


class Localisation(str, Enum):
    AM_NORTH = "AM_NORTH"
    AM_SOUTH = "AM_SOUTH"
    ANTIL_GUY = "ANTIL_GUY"
    ASIA = "ASIA"


_LOCALISATION_MAP = {
    "amérique du nord": Localisation.AM_NORTH,
    "amerique du nord": Localisation.AM_NORTH,
    "amérique du sud": Localisation.AM_SOUTH,
    "amerique du sud": Localisation.AM_SOUTH,
    "antilles, guyane": Localisation.ANTIL_GUY,
    "antilles , guyane": Localisation.ANTIL_GUY,
    "antilles guyane": Localisation.ANTIL_GUY,
    "asie": Localisation.ASIA,
}


def normalize_localisation(text: str) -> Optional[Localisation]:
    if not text:
        return None
    key = text.strip().lower()
    return _LOCALISATION_MAP.get(key)


class SessionType(str, Enum):
    NORMAL = "NORMAL"
    REMPLACEMENT = "REMPLACEMENT"


def normalize_session(text: str) -> Tuple[Optional[str], Optional[SessionType]]:
    """
    Convert strings like "2024 - épreuves normales" to ("2024_NORMAL", SessionType.NORMAL).
    Returns (code, session_enum). If parsing fails, returns (None, None).
    """
    if not text:
        return None, None
    t = text.strip().lower()

    # Extract year (2000-2099) or leading 2 digits (e.g., 24 -> 2024)
    year: Optional[str] = None
    m = re.search(r"\b(20[0-9]{2})\b", t)
    if m:
        year = m.group(1)
    else:
        m2 = re.match(r"^(\d{2})", t)
        if m2:
            year = f"20{m2.group(1)}"

    session_kind: Optional[SessionType] = None
    if re.search(r"\b(normal|normale|normales)\b", t):
        session_kind = SessionType.NORMAL
    elif re.search(r"\b(remplacement|septembre)\b", t):
        session_kind = SessionType.REMPLACEMENT

    if year and session_kind:
        return f"{year}_{session_kind.value}", session_kind
    return None, session_kind


class Serie(str, Enum):
    GENERALE = "GENERALE"
    PROFESSIONNELLE = "PROFESSIONNELLE"


def normalize_serie(text: str) -> Optional[Serie]:
    if not text:
        return None
    t = text.strip().lower()
    if re.search(r"\b(générale|generale|gen)\b", t):
        return Serie.GENERALE
    if re.search(r"\b(professionnelle|professionnel|pro)\b", t):
        return Serie.PROFESSIONNELLE
    return None



class Discipline(str, Enum):
    # Example provided in the request
    FR_DICTEE = "FR_DICTEE"


def normalize_discipline(text: str) -> Optional[Discipline]:
    """
    Convert strings like "Français - dictée" to Discipline.FR_DICTEE.
    Returns None if not recognized.
    """
    if not text:
        return None
    t = text.strip().lower()
    if ("fran" in t or re.search(r"\bfrançais|francais\b", t)) and (
        "dict" in t or re.search(r"\bdictée|dictee\b", t)
    ):
        return Discipline.FR_DICTEE
    return None


