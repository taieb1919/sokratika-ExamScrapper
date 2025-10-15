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
    LIBAN = "LIBAN"
    METROPOLE = "METROPOLE"
    METRO_ANTIL_GUY = "METRO_ANTIL_GUY"
    NOUVELLE_CAL = "NOUVELLE_CAL"
    GROUPE_1 = "GROUPE_1"
    POLYNESIE = "POLYNESIE"
    PONDICHERY = "PONDICHERY"


_LOCALISATION_MAP = {
    "amérique du nord": Localisation.AM_NORTH,
    "amerique du nord": Localisation.AM_NORTH,
    "amérique du sud": Localisation.AM_SOUTH,
    "amerique du sud": Localisation.AM_SOUTH,
    "antilles, guyane": Localisation.ANTIL_GUY,
    "antilles , guyane": Localisation.ANTIL_GUY,
    "antilles guyane": Localisation.ANTIL_GUY,
    "asie": Localisation.ASIA,
    "liban": Localisation.LIBAN,
    "métropole": Localisation.METROPOLE,
    "metropole": Localisation.METROPOLE,
    "métropole et antilles-guyane": Localisation.METRO_ANTIL_GUY,
    "metropole et antilles-guyane": Localisation.METRO_ANTIL_GUY,
    "nouvelle-calédonie": Localisation.NOUVELLE_CAL,
    "nouvelle caledonie": Localisation.NOUVELLE_CAL,
    "groupe 1": Localisation.GROUPE_1,
    "polynésie": Localisation.POLYNESIE,
    "polynesie": Localisation.POLYNESIE,
    "pondichéry": Localisation.PONDICHERY,
    "pondichery": Localisation.PONDICHERY,
}


def normalize_localisation(text: str) -> Optional[Localisation]:
    if not text:
        return None
    key = text.strip().lower()
    if key in _LOCALISATION_MAP:
        return _LOCALISATION_MAP[key]

    t = re.sub(r"\s+", " ", key)
    # Regex fallbacks
    if re.search(r"am[ée]rique\s+du\s+nord", t):
        return Localisation.AM_NORTH
    if re.search(r"am[ée]rique\s+du\s+sud", t):
        return Localisation.AM_SOUTH
    if re.search(r"antilles\s*,?\s*guyane", t):
        return Localisation.ANTIL_GUY
    if re.search(r"m[ée]tropole\s+et\s+antilles[- ]guyane", t):
        return Localisation.METRO_ANTIL_GUY
    if re.search(r"m[ée]tropole|metropole", t):
        return Localisation.METROPOLE
    if re.search(r"nouvelle[- ]cal[ée]donie", t):
        return Localisation.NOUVELLE_CAL
    if re.search(r"polyn[ée]sie", t):
        return Localisation.POLYNESIE
    if re.search(r"pondich[ée]ry", t):
        return Localisation.PONDICHERY
    if re.search(r"\bgroupe\s*1\b", t):
        return Localisation.GROUPE_1
    if re.search(r"\bliban\b", t):
        return Localisation.LIBAN
    if re.search(r"\basie\b", t):
        return Localisation.ASIA
    return None


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
    TOUTES = "TOUTES"


def normalize_serie(text: str) -> Optional[Serie]:
    if not text:
        return None
    t = text.strip().lower()
    if re.search(r"\b(générale|generale|gen)\b", t):
        return Serie.GENERALE
    if re.search(r"\b(professionnelle|professionnel|pro)\b", t):
        return Serie.PROFESSIONNELLE
    if re.search(r"\btoutes\b", t):
        return Serie.TOUTES
    return None



class Discipline(str, Enum):
    # Français
    FR_DICTEE = "FR_DICTEE"
    FR_GRAM_COMP = "FR_GRAM_COMP"
    FR_REDACTION = "FR_REDACTION"

    # Histoire-Géo-EMC
    HIST_GEO_EMC = "HIST_GEO_EMC"

    # Langues Vivantes
    LV_ALLEMAND = "LV_ALLEMAND"
    LV_ANGLAIS = "LV_ANGLAIS"
    LV_ARABE = "LV_ARABE"
    LV_CHINOIS = "LV_CHINOIS"
    LV_ESPAGNOL = "LV_ESPAGNOL"
    LV_GREC = "LV_GREC"
    LV_HEBREU = "LV_HEBREU"
    LV_ITALIEN = "LV_ITALIEN"
    LV_JAPONAIS = "LV_JAPONAIS"
    LV_PORTUGAIS = "LV_PORTUGAIS"
    LV_RUSSE = "LV_RUSSE"
    LV_TURC = "LV_TURC"

    # Mathématiques et Sciences
    MATHS = "MATHS"
    SCIENCES = "SCIENCES"


def normalize_discipline(text: str) -> Optional[Discipline]:
    """
    Convert strings like "Français - dictée" to Discipline.FR_DICTEE.
    Returns None if not recognized.
    """
    if not text:
        return None
    t = text.strip().lower()
    # Français - dictée
    if ("fran" in t or re.search(r"\bfrançais|francais\b", t)) and (
        "dict" in t or re.search(r"\bdict[ée]e\b", t)
    ):
        return Discipline.FR_DICTEE

    # Français - grammaire / compréhension
    if re.search(r"\bfran[çc]ais\b", t) and re.search(r"\b(grammaire|compr[ée]hension|questions?)\b", t):
        return Discipline.FR_GRAM_COMP

    # Français - rédaction
    if re.search(r"\bfran[çc]ais\b", t) and re.search(r"\br[ée]daction\b", t):
        return Discipline.FR_REDACTION

    # Histoire-Géographie-EMC
    if re.search(r"histo(i)?re|g[ée]ographie|\bemc\b", t):
        return Discipline.HIST_GEO_EMC

    # Langues Vivantes (match language names)
    if re.search(r"\ballemand\b", t):
        return Discipline.LV_ALLEMAND
    if re.search(r"\banglais\b", t):
        return Discipline.LV_ANGLAIS
    if re.search(r"\barabe\b", t):
        return Discipline.LV_ARABE
    if re.search(r"\bchinois\b", t):
        return Discipline.LV_CHINOIS
    if re.search(r"\bespagnol\b", t):
        return Discipline.LV_ESPAGNOL
    if re.search(r"\bgrec\b", t):
        return Discipline.LV_GREC
    if re.search(r"\bh[ée]breu\b", t):
        return Discipline.LV_HEBREU
    if re.search(r"\bitalien\b", t):
        return Discipline.LV_ITALIEN
    if re.search(r"\bjaponais\b", t):
        return Discipline.LV_JAPONAIS
    if re.search(r"\bportugais\b", t):
        return Discipline.LV_PORTUGAIS
    if re.search(r"\brusse\b", t):
        return Discipline.LV_RUSSE
    if re.search(r"\bturc\b", t):
        return Discipline.LV_TURC

    # Mathématiques
    if re.search(r"\bmath(ématiques|ematiques|s)?\b|\bmaths\b", t):
        return Discipline.MATHS

    # Sciences (inclut SVT, Physique, Chimie, Technologie)
    if re.search(r"\bsciences?\b|\bsvt\b|physique|chimie|technologie", t):
        return Discipline.SCIENCES
    return None


