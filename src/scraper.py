"""
Web scraper for DNB exam papers with Selenium pagination support.

This module provides the DNBScraper class which handles:
- Fetching web pages with Selenium WebDriver
- Navigating through pagination
- Extracting PDF download links from /document/*/download format
- Parsing data-atl-name attributes for metadata
"""

import time
import re
from typing import List, Dict, Optional, Set, Tuple
from urllib.parse import urljoin
from loguru import logger
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    ElementNotInteractableException,
    StaleElementReferenceException
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

from config.settings import (
    BASE_URL,
    SELENIUM_HEADLESS,
    SELENIUM_TIMEOUT,
    SELENIUM_PAGE_LOAD_WAIT,
    MAX_RETRIES,
)
from src.parser import MetadataParser
from src.enums import (
    Localisation,
    SessionType,
    Serie,
    TypeDocument,
    Discipline,
    normalize_localisation,
    normalize_session,
    normalize_serie,
    normalize_type_document,
    normalize_discipline,
)


class DNBScraper:
    """
    Scraper for DNB (Diplôme National du Brevet) exam papers with pagination support.
    
    This class uses Selenium WebDriver to handle JavaScript-based pagination
    and extract all PDF download links across multiple pages.
    
    The HTML structure is:
    - Pagination with buttons: Premier, Précédent, [1][2][3]..., Suivant, Dernier
    - <tbody> contains rows <tr>
    - Each <tr> has columns: Session, Discipline, Série, Localisation, Liens
    - Links are in <td> with class "views-field-link"
    - Link format: <a href="/document/[ID]/download">
    - data-atl-name contains the PDF filename (e.g., "24genfrdag1_v11.pdf|63414")
    
    Attributes:
        base_url: The base URL to scrape
        driver: Selenium WebDriver instance
        parser: MetadataParser instance for link analysis
        headless: Run browser in headless mode
    
    Example:
        >>> scraper = DNBScraper()
        >>> pdf_links = scraper.extract_pdf_links()
        >>> print(f"Found {len(pdf_links)} PDF files")
        >>> summary = scraper.get_summary_dict()
        >>> print(f"Total: {summary['total']}")
    """
    
    def __init__(self, base_url: str = BASE_URL, headless: bool = SELENIUM_HEADLESS):
        """
        Initialize the DNB scraper with Selenium.
        
        Args:
            base_url: The URL to scrape (default: from settings)
            headless: Run browser in headless mode (default: from settings)
        """
        self.base_url = base_url
        self.headless = headless
        self.driver: Optional[webdriver.Chrome] = None
        self.parser = MetadataParser()
        self.pdf_links: List[Dict[str, str]] = []  # List of {url, data_atl_name}
        
        logger.info(f"DNBScraper initialized with URL: {base_url} (headless: {headless})")
    
    def _init_driver(self) -> webdriver.Chrome:
        """
        Initialize Selenium Chrome WebDriver.
        
        Returns:
            Chrome WebDriver instance
        """
        logger.info("Initializing Selenium WebDriver")
        
        chrome_options = Options()
        
        if self.headless:
            chrome_options.add_argument("--headless=new")
            logger.debug("Running in headless mode")
        
        # Additional options for stability
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)
        
        # User agent
        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        try:
            driver = webdriver.Chrome(options=chrome_options)
            driver.implicitly_wait(10)
            logger.success("WebDriver initialized successfully")
            return driver
        except Exception as e:
            logger.error(f"Failed to initialize WebDriver: {e}")
            logger.warning("Make sure Chrome and ChromeDriver are installed")
            raise
    
    def _extract_links_from_current_page(self) -> List[Dict[str, str]]:
        """
        Extract all PDF links from the current page.
        
        Returns:
            List of dictionaries with 'url' and 'data_atl_name' keys
        """
        pdf_data: List[Dict[str, str]] = []
        
        # Get page source and parse with BeautifulSoup
        page_source = self.driver.page_source
        soup = BeautifulSoup(page_source, 'lxml')
        
        # Find table rows to also extract column text when available
        all_links = soup.find_all('a', href=True)
        
        for link in all_links:
            href = link['href']
            
            # Skip empty links
            if not href:
                continue
            
            # Check if it's a PDF download link
            if self._is_pdf_link(href):
                # Convert relative URLs to absolute
                absolute_url = urljoin(self.base_url, href)
                
                # Extract data-atl-name attribute if present
                data_atl_name = link.get('data-atl-name', '')
                
                pdf_data.append({
                    'url': absolute_url,
                    'data_atl_name': data_atl_name
                })
                
                logger.debug(f"Found PDF: {absolute_url} | data-atl-name: {data_atl_name}")
        
        return pdf_data

    def extract_distinct_table_values(self) -> Dict[str, Set[str]]:
        """
        Extract distinct values for table columns (Session, Discipline, Série, Localisation)
        from the current page source. This relies on the page structure described in README.

        Returns a dict with keys: 'Session', 'Discipline', 'Serie', 'Localisation', 'TypeDocument'
        """
        if not self.driver:
            return {k: set() for k in ['Session', 'Discipline', 'Serie', 'Localisation', 'TypeDocument']}

        soup = BeautifulSoup(self.driver.page_source, 'lxml')
        values: Dict[str, Set[str]] = {
            'Session': set(),
            'Discipline': set(),
            'Serie': set(),
            'Localisation': set(),
            'TypeDocument': set(),
        }

        tbody = soup.find('tbody')
        if not tbody:
            return values

        for tr in tbody.find_all('tr'):
            tds = tr.find_all('td')
            if len(tds) < 5:
                continue
            session_txt = tds[0].get_text(strip=True)
            discipline_txt = tds[1].get_text(strip=True)
            serie_txt = tds[2].get_text(strip=True)
            localisation_txt = tds[3].get_text(strip=True)
            link_td = tds[4]
            link = link_td.find('a', href=True)
            type_txt = ''
            if link is not None:
                data_atl = link.get('data-atl-name', '')
                meta = self.parser.parse_url(link['href'], data_atl)
                type_txt = 'correction' if meta.get('document_type') == 'correction' else 'sujet'

            if session_txt:
                values['Session'].add(session_txt)
            if discipline_txt:
                values['Discipline'].add(discipline_txt)
            if serie_txt:
                values['Serie'].add(serie_txt)
            if localisation_txt:
                values['Localisation'].add(localisation_txt)
            if type_txt:
                values['TypeDocument'].add(type_txt)

        return values
    
    def _is_pdf_link(self, url: str) -> bool:
        """
        Check if a URL points to a PDF download.
        
        Matches URLs in the format: /document/*/download
        
        Args:
            url: URL to check
        
        Returns:
            True if URL matches /document/*/download pattern, False otherwise
        """
        pattern = r'/document/[^/]+/download'
        return bool(re.search(pattern, url))
    
    def _click_next_page(self) -> bool:
        """
        Click the "Suivant" (Next) button to go to the next page.
        
        Uses JavaScript click to avoid ElementClickInterceptedException.
        
        Returns:
            True if successfully clicked and navigated, False if no more pages
        """
        try:
            # Wait for the "Suivant" button with simplified selector
            # Try primary selector: a[rel='next']
            next_button = None
            
            try:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a[rel='next']"))
                )
            except TimeoutException:
                # Fallback: try title attribute
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "a[title*='page suivante']"))
                    )
                except TimeoutException:
                    logger.info("No more pages - 'Suivant' button not found")
                    return False
            
            # Check if button is disabled
            if next_button:
                button_class = next_button.get_attribute('class') or ''
                parent = next_button.find_element(By.XPATH, "..")
                parent_class = parent.get_attribute('class') or ''
                
                if 'is-disabled' in button_class or 'is-disabled' in parent_class:
                    logger.info("No more pages - 'Suivant' button is disabled")
                    return False
                
                # Use JavaScript click to avoid interception errors
                logger.debug("Clicking 'Suivant' button with JavaScript")
                self.driver.execute_script("arguments[0].click();", next_button)
                logger.info("Clicked 'Suivant' button")
                
                # Wait for page to load
                time.sleep(SELENIUM_PAGE_LOAD_WAIT)
                
                # Wait for the table to be present again
                WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                    EC.presence_of_element_located((By.TAG_NAME, "tbody"))
                )
                
                return True
            else:
                logger.info("No more pages - 'Suivant' button not found")
                return False
        
        except (NoSuchElementException, TimeoutException) as e:
            logger.info(f"Reached last page: {type(e).__name__}")
            return False
        except StaleElementReferenceException:
            logger.warning("Stale element reference, retrying...")
            time.sleep(1)
            return self._click_next_page()
        except Exception as e:
            logger.error(f"Error clicking next page: {e}")
            return False
    
    def extract_pdf_links(self, url: Optional[str] = None, max_pages: Optional[int] = None) -> List[Dict[str, str]]:
        """
        Extract all PDF download links from all pages.
        
        This method:
        1. Initializes the WebDriver
        2. Navigates to the target page
        3. Extracts links from the first page
        4. Navigates through all pages using the "Suivant" button
        5. Extracts links from each page
        6. Returns all unique links
        
        Args:
            url: URL to scrape (default: base_url)
            max_pages: If provided, stops after scraping this many pages
        
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
        if url is None:
            url = self.base_url
        
        all_pdf_data: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()
        
        try:
            # Initialize WebDriver
            self.driver = self._init_driver()
            
            # Navigate to the page
            logger.info(f"Navigating to: {url}")
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, SELENIUM_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            logger.success("Page loaded successfully")
            
            # Close any overlays, modals, or cookie banners that might intercept clicks
            try:
                logger.debug("Checking for overlays/modals to close")
                close_selectors = [
                    ".close", 
                    "[aria-label='Close']", 
                    ".modal-close",
                    ".cookie-banner .close",
                    "button.close",
                    ".overlay-close"
                ]
                for selector in close_selectors:
                    try:
                        close_buttons = self.driver.find_elements(By.CSS_SELECTOR, selector)
                        for btn in close_buttons:
                            if btn.is_displayed():
                                self.driver.execute_script("arguments[0].click();", btn)
                                logger.debug(f"Closed overlay with selector: {selector}")
                                time.sleep(0.5)
                    except Exception:
                        pass
            except Exception as e:
                logger.debug(f"No overlays to close or error: {e}")
            
            # Extract links from all pages
            page_number = 1
            while True:
                logger.info(f"Extracting links from page {page_number}")
                
                # Extract links from current page
                pdf_data = self._extract_links_from_current_page()
                
                # Add unique links
                new_links = 0
                for link_data in pdf_data:
                    if link_data['url'] not in seen_urls:
                        seen_urls.add(link_data['url'])
                        all_pdf_data.append(link_data)
                        new_links += 1
                
                logger.info(f"Page {page_number}: Found {new_links} new PDF links")

                # Stop if we reached the requested max_pages
                if max_pages is not None and page_number >= max_pages:
                    logger.info(f"Reached max pages limit ({max_pages}), stopping pagination")
                    break
                
                # Try to go to next page
                if not self._click_next_page():
                    logger.info("No more pages to process")
                    break
                
                page_number += 1
                
                # Safety limit to prevent infinite loops
                if page_number > 100:
                    logger.warning("Reached maximum page limit (100)")
                    break
            
            self.pdf_links = all_pdf_data
            logger.success(f"Extracted {len(self.pdf_links)} unique PDF download links from {page_number} pages")
            
            return self.pdf_links
        
        except Exception as e:
            logger.error(f"Error during extraction: {e}")
            raise
        finally:
            # Always close the driver
            if self.driver:
                self.close()
    
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
        Close the Selenium WebDriver.
        
        Returns:
            None
        """
        if self.driver:
            try:
                self.driver.quit()
                logger.debug("WebDriver closed")
            except Exception as e:
                logger.warning(f"Error closing WebDriver: {e}")
            finally:
                self.driver = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
