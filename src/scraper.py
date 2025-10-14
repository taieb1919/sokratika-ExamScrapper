"""
Web scraper for DNB exam papers.

This module provides the DNBScraper class which handles:
- Fetching web pages
- Extracting PDF download links from /document/*/download format
- Parsing data-atl-name attributes for metadata
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from loguru import logger

from config.settings import (
    BASE_URL,
    HEADERS,
    DOWNLOAD_TIMEOUT,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    VERIFY_SSL,
)
from src.utils import rate_limited, retry_on_failure, is_valid_url
from src.parser import MetadataParser


class DNBScraper:
    """
    Scraper for DNB (Diplôme National du Brevet) exam papers.
    
    This class handles fetching the DNB annales page and extracting
    all PDF download links in the format /document/*/download.
    
    The HTML structure is:
    - <tbody> contains rows <tr>
    - Each <tr> has columns: Session, Discipline, Série, Localisation, Liens
    - Links are in <td> with class "views-field-link"
    - Link format: <a href="/document/[ID]/download">
    - data-atl-name contains the PDF filename (e.g., "24genfrdag1_v11.pdf|63414")
    
    Attributes:
        base_url: The base URL to scrape
        session: Requests session for HTTP connections
        parser: MetadataParser instance for link analysis
    
    Example:
        >>> scraper = DNBScraper()
        >>> pdf_links = scraper.extract_pdf_links()
        >>> print(f"Found {len(pdf_links)} PDF files")
        >>> summary = scraper.get_summary_dict()
        >>> print(f"Total: {summary['total']}")
    """
    
    def __init__(self, base_url: str = BASE_URL):
        """
        Initialize the DNB scraper.
        
        Args:
            base_url: The URL to scrape (default: from settings)
        """
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.parser = MetadataParser()
        self.html_content: Optional[str] = None
        self.soup: Optional[BeautifulSoup] = None
        self.pdf_links: List[Dict[str, str]] = []  # List of {url, data_atl_name}
        
        logger.info(f"DNBScraper initialized with URL: {base_url}")
    
    @retry_on_failure(
        max_retries=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        exceptions=(requests.RequestException,)
    )
    @rate_limited()
    def fetch_page(self, url: Optional[str] = None) -> str:
        """
        Fetch the HTML content of a web page.
        
        Args:
            url: URL to fetch (default: base_url)
        
        Returns:
            HTML content as string
        
        Raises:
            requests.RequestException: If the request fails
        
        Example:
            >>> scraper = DNBScraper()
            >>> html = scraper.fetch_page()
        """
        if url is None:
            url = self.base_url
        
        logger.info(f"Fetching page: {url}")
        
        try:
            response = self.session.get(
                url,
                timeout=DOWNLOAD_TIMEOUT,
                verify=VERIFY_SSL
            )
            response.raise_for_status()
            
            self.html_content = response.text
            logger.success(f"Successfully fetched page ({len(self.html_content)} bytes)")
            
            return self.html_content
            
        except requests.HTTPError as e:
            logger.error(f"HTTP error fetching {url}: {e}")
            raise
        except requests.ConnectionError as e:
            logger.error(f"Connection error fetching {url}: {e}")
            raise
        except requests.Timeout as e:
            logger.error(f"Timeout fetching {url}: {e}")
            raise
        except requests.RequestException as e:
            logger.error(f"Request error fetching {url}: {e}")
            raise
    
    def parse_html(self, html: Optional[str] = None) -> BeautifulSoup:
        """
        Parse HTML content into BeautifulSoup object.
        
        Args:
            html: HTML content to parse (default: self.html_content)
        
        Returns:
            BeautifulSoup object
        
        Raises:
            ValueError: If no HTML content is available
        """
        if html is None:
            if self.html_content is None:
                raise ValueError("No HTML content to parse. Call fetch_page() first.")
            html = self.html_content
        
        logger.debug("Parsing HTML content")
        self.soup = BeautifulSoup(html, 'lxml')
        return self.soup
    
    def extract_pdf_links(self, url: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Extract all PDF download links from the page.
        
        Searches for links in the format /document/*/download and extracts
        their data-atl-name attributes for metadata.
        
        Args:
            url: URL to scrape (default: base_url)
        
        Returns:
            List of dictionaries with 'url' and 'data_atl_name' keys
        
        Example:
            >>> scraper = DNBScraper()
            >>> pdf_links = scraper.extract_pdf_links()
            >>> print(f"Found {len(pdf_links)} PDFs")
            >>> print(pdf_links[0]['url'])
            '/document/123/download'
            >>> print(pdf_links[0]['data_atl_name'])
            '24genfrdag1_v11.pdf|63414'
        """
        # Fetch and parse the page
        if url is not None or self.html_content is None:
            self.fetch_page(url)
        
        if self.soup is None:
            self.parse_html()
        
        logger.info("Extracting PDF download links from page")
        
        pdf_data: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()
        
        # Find all links
        all_links = self.soup.find_all('a', href=True)
        logger.debug(f"Found {len(all_links)} total links on page")
        
        for link in all_links:
            href = link['href']
            
            # Skip empty links
            if not href:
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(self.base_url, href)
            
            # Check if it's a PDF download link
            if self._is_pdf_link(href):
                # Avoid duplicates
                if absolute_url in seen_urls:
                    continue
                
                seen_urls.add(absolute_url)
                
                # Extract data-atl-name attribute if present
                data_atl_name = link.get('data-atl-name', '')
                
                pdf_data.append({
                    'url': absolute_url,
                    'data_atl_name': data_atl_name
                })
                
                logger.debug(f"Found PDF: {absolute_url} | data-atl-name: {data_atl_name}")
        
        self.pdf_links = pdf_data
        logger.success(f"Extracted {len(self.pdf_links)} unique PDF download links")
        
        return self.pdf_links
    
    def _is_pdf_link(self, url: str) -> bool:
        """
        Check if a URL points to a PDF download.
        
        Matches URLs in the format: /document/*/download
        
        Args:
            url: URL to check
        
        Returns:
            True if URL matches /document/*/download pattern, False otherwise
        """
        # Check for /document/*/download pattern
        import re
        pattern = r'/document/[^/]+/download'
        
        if re.search(pattern, url):
            return True
        
        return False
    
    def get_summary_dict(self) -> Dict:
        """
        Get summary statistics of extracted PDFs.
        
        Returns:
            Dictionary with summary statistics including:
            - total: total number of PDFs
            - by_year: count by year
            - by_subject: count by subject
            - by_type: count by document type (sujet/correction)
            - years: list of available years
            - subjects: list of available subjects
        
        Example:
            >>> scraper = DNBScraper()
            >>> scraper.extract_pdf_links()
            >>> summary = scraper.get_summary_dict()
            >>> print(f"Total PDFs: {summary['total']}")
            >>> print(f"Years: {summary['years']}")
        """
        if not self.pdf_links:
            logger.warning("No PDF links extracted yet. Call extract_pdf_links() first.")
            return {
                'total': 0,
                'by_year': {},
                'by_subject': {},
                'by_type': {'sujet': 0, 'correction': 0},
                'years': [],
                'subjects': [],
            }
        
        stats = {
            'total': len(self.pdf_links),
            'by_year': {},
            'by_subject': {},
            'by_type': {'sujet': 0, 'correction': 0},
            'years': set(),
            'subjects': set(),
        }
        
        for pdf_data in self.pdf_links:
            # Parse metadata
            metadata = self.parser.parse_url(
                pdf_data['url'], 
                pdf_data.get('data_atl_name')
            )
            
            # Count by year
            year = metadata.get('year')
            if year:
                stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
                stats['years'].add(year)
            
            # Count by subject
            subject = metadata.get('subject')
            if subject:
                stats['by_subject'][subject] = stats['by_subject'].get(subject, 0) + 1
                stats['subjects'].add(subject)
            
            # Count by type
            doc_type = metadata.get('document_type', 'sujet')
            stats['by_type'][doc_type] = stats['by_type'].get(doc_type, 0) + 1
        
        # Convert sets to sorted lists
        stats['years'] = sorted(list(stats['years']), reverse=True)
        stats['subjects'] = sorted(list(stats['subjects']))
        
        logger.info(f"Summary: {stats['total']} PDFs, {len(stats['years'])} years, {len(stats['subjects'])} subjects")
        
        return stats
    
    def close(self) -> None:
        """
        Close the HTTP session.
        
        Returns:
            None
        """
        self.session.close()
        logger.debug("HTTP session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
