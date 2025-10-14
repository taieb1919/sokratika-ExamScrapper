"""
DNB Annales Scraper - A professional tool for downloading DNB exam papers.

This package provides tools to scrape and download PDF files of DNB (Diplôme National du Brevet)
exam papers from the French education website.
"""

__version__ = "1.0.0"
__author__ = "Sokratika"
__email__ = "contact@sokratika.com"

from src.scraper import DNBScraper
from src.downloader import PDFDownloader
from src.parser import MetadataParser

__all__ = ["DNBScraper", "PDFDownloader", "MetadataParser"]

