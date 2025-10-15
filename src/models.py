"""
Data models for structured DNB scraping results.

Defines dataclasses used to represent files and exam entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from src.enums import SessionType, Discipline, Serie, Localisation


@dataclass(frozen=True)
class File:
    filename: str
    download_url: str


@dataclass
class ExamEntry:
    id: int
    session: SessionType
    discipline: Discipline
    serie: Serie
    localisation: Localisation
    files: List[File] = field(default_factory=list)


