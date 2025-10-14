"""
Configuration settings for DNB Annales Scraper.

This module contains all configuration variables for the scraper,
including URLs, file paths, and scraping parameters.
"""

import os
from pathlib import Path
from typing import Dict

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
METADATA_DIR = DATA_DIR / "metadata"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
for directory in [DATA_DIR, RAW_DATA_DIR, METADATA_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Target URL
BASE_URL = "https://eduscol.education.fr/711/preparer-le-diplome-national-du-brevet-dnb-avec-les-sujets-des-annales"

# HTTP Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

# Rate limiting
REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.5"))  # seconds between requests
DOWNLOAD_TIMEOUT = int(os.getenv("DOWNLOAD_TIMEOUT", "30"))  # seconds
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_BACKOFF_FACTOR = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

# Download settings
MAX_WORKERS = int(os.getenv("MAX_WORKERS", "5"))  # concurrent downloads
CHUNK_SIZE = 8192  # bytes for streaming downloads
VERIFY_SSL = os.getenv("VERIFY_SSL", "True").lower() == "true"

# Selenium settings
SELENIUM_HEADLESS = os.getenv("SELENIUM_HEADLESS", "True").lower() == "true"
SELENIUM_TIMEOUT = int(os.getenv("SELENIUM_TIMEOUT", "20"))  # seconds
SELENIUM_PAGE_LOAD_WAIT = float(os.getenv("SELENIUM_PAGE_LOAD_WAIT", "2.0"))  # seconds between page loads

# File organization
ORGANIZE_BY_YEAR = os.getenv("ORGANIZE_BY_YEAR", "True").lower() == "true"
ORGANIZE_BY_SUBJECT = os.getenv("ORGANIZE_BY_SUBJECT", "True").lower() == "true"

# Subjects mapping for French educational system
SUBJECTS_MAP: Dict[str, str] = {
    "mathematiques": "Mathématiques",
    "maths": "Mathématiques",
    "francais": "Français",
    "histoire": "Histoire-Géographie",
    "geographie": "Histoire-Géographie",
    "histoire-geographie": "Histoire-Géographie",
    "sciences": "Sciences",
    "svt": "Sciences (SVT)",
    "physique": "Sciences (Physique-Chimie)",
    "chimie": "Sciences (Physique-Chimie)",
    "technologie": "Sciences (Technologie)",
    "anglais": "Anglais LV1",
    "allemand": "Allemand LV1",
    "espagnol": "Espagnol LV1",
    "italien": "Italien LV1",
}

# Session types
SESSION_TYPES = ["normale", "remplacement", "septembre", "juin"]

# Series
SERIES_TYPES = ["generale", "professionnelle", "pro"]

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
LOG_ROTATION = "10 MB"
LOG_RETENTION = "30 days"

# Metadata
METADATA_FILE = METADATA_DIR / "downloads_metadata.json"
FAILED_DOWNLOADS_FILE = METADATA_DIR / "failed_downloads.json"

# PDF Validation
MIN_PDF_SIZE = 1024  # bytes (1 KB minimum)
PDF_MAGIC_BYTES = b"%PDF"

