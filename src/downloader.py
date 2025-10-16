"""
PDF downloader for DNB exam papers.

This module provides the PDFDownloader class which handles:
- Downloading individual PDFs
- Batch downloading with multi-threading
- PDF validation
- Progress tracking
"""

import requests
import json
from pathlib import Path
from typing import List, Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from loguru import logger
from tqdm import tqdm

from config.settings import (
    RAW_DATA_DIR,
    METADATA_DIR,
    HEADERS,
    DOWNLOAD_TIMEOUT,
    MAX_WORKERS,
    CHUNK_SIZE,
    MIN_PDF_SIZE,
    PDF_MAGIC_BYTES,
    MAX_RETRIES,
    RETRY_BACKOFF_FACTOR,
    VERIFY_SSL,
    ORGANIZE_BY_YEAR,
    ORGANIZE_BY_SUBJECT,
    METADATA_FILE,
    FAILED_DOWNLOADS_FILE,
)
from src.utils import (
    rate_limited,
    retry_on_failure,
    ensure_directory,
    format_bytes,
    extract_filename_from_url,
    create_directory_structure,
)
from src.parser import MetadataParser


class PDFDownloader:
    """
    Downloader for PDF files with support for batch downloads and validation.
    
    This class handles downloading PDF files with features like:
    - Multi-threaded batch downloads
    - Automatic retries with exponential backoff
    - PDF validation
    - Progress tracking
    - Metadata tracking
    
    Attributes:
        output_dir: Directory where PDFs will be saved
        session: Requests session for HTTP connections
        parser: MetadataParser for organizing files
    
    Example:
        >>> downloader = PDFDownloader(output_dir="data/raw")
        >>> downloader.download_pdf("https://example.com/file.pdf")
        >>> downloader.batch_download(pdf_links, max_workers=5)
    """
    
    def __init__(self, output_dir: Path = RAW_DATA_DIR):
        """
        Initialize the PDF downloader.
        
        Args:
            output_dir: Directory to save downloaded PDFs
        """
        self.output_dir = Path(output_dir)
        ensure_directory(self.output_dir)
        
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        self.parser = MetadataParser()
        self.download_history: List[Dict] = []
        self.failed_downloads: List[Dict] = []
        
        logger.info(f"PDFDownloader initialized with output_dir: {self.output_dir}")
    
    def check_existing(self, filepath: Path) -> bool:
        """
        Check if a file already exists and is valid.
        
        Args:
            filepath: Path to check
        
        Returns:
            True if file exists and is valid, False otherwise
        """
        if not filepath.exists():
            return False
        
        # Check file size
        if filepath.stat().st_size < MIN_PDF_SIZE:
            logger.warning(f"Existing file too small: {filepath}")
            return False
        
        # Quick validation
        if not self.validate_pdf(filepath):
            logger.warning(f"Existing file invalid: {filepath}")
            return False
        
        logger.debug(f"File already exists: {filepath}")
        return True
    
    def validate_pdf(self, filepath: Path) -> bool:
        """
        Validate that a file is a valid PDF.
        
        Args:
            filepath: Path to the PDF file
        
        Returns:
            True if valid PDF, False otherwise
        """
        try:
            # Check file size
            if filepath.stat().st_size < MIN_PDF_SIZE:
                logger.warning(f"File too small to be a valid PDF: {filepath}")
                return False
            
            # Check magic bytes
            with open(filepath, 'rb') as f:
                header = f.read(len(PDF_MAGIC_BYTES))
                if not header.startswith(PDF_MAGIC_BYTES):
                    logger.warning(f"Invalid PDF magic bytes: {filepath}")
                    return False
            
            logger.debug(f"PDF validation passed: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Error validating PDF {filepath}: {e}")
            return False
    
    @retry_on_failure(
        max_retries=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        exceptions=(requests.RequestException,)
    )
    @rate_limited()
    def download_pdf(
        self,
        url: str,
        output_path: Optional[Path] = None,
        metadata: Optional[Dict] = None,
        skip_existing: bool = True,
        organize: bool = True,
    ) -> Optional[Path]:
        """
        Download a single PDF file.
        
        Args:
            url: URL of the PDF to download
            output_path: Custom output path (optional)
            metadata: Metadata dictionary for the file
            skip_existing: Skip if file already exists
            organize: Organize files by year/subject
        
        Returns:
            Path to downloaded file, or None if failed/skipped
        
        Example:
            >>> downloader = PDFDownloader()
            >>> path = downloader.download_pdf("https://example.com/file.pdf")
        """
        logger.info(f"Downloading: {url}")
        
        # Parse metadata if not provided
        if metadata is None:
            metadata = self.parser.parse_url(url)
        
        # Determine output path
        if output_path is None:
            if organize and (ORGANIZE_BY_YEAR or ORGANIZE_BY_SUBJECT):
                year = metadata.get('year') if ORGANIZE_BY_YEAR else None
                subject = metadata.get('subject') if ORGANIZE_BY_SUBJECT else None
                base_dir = create_directory_structure(self.output_dir, year, subject)
            else:
                base_dir = self.output_dir
            
            # Generate filename
            filename = self.parser.generate_organized_filename(metadata)
            output_path = base_dir / filename
        
        # Check if already exists
        if skip_existing and self.check_existing(output_path):
            logger.info(f"Skipping existing file: {output_path}")
            return output_path
        
        try:
            # Download with streaming
            response = self.session.get(
                url,
                timeout=DOWNLOAD_TIMEOUT,
                stream=True,
                verify=VERIFY_SSL
            )
            response.raise_for_status()
            
            # Get file size from headers
            total_size = int(response.headers.get('content-length', 0))
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Download with progress
            downloaded_size = 0
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
            
            logger.debug(f"Downloaded {format_bytes(downloaded_size)}")
            
            # Validate downloaded file
            if not self.validate_pdf(output_path):
                logger.error(f"Downloaded file is not a valid PDF: {output_path}")
                output_path.unlink(missing_ok=True)
                return None
            
            # Record successful download
            download_record = {
                'url': url,
                'filepath': str(output_path),
                'size': downloaded_size,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata,
            }
            self.download_history.append(download_record)
            
            logger.success(f"Successfully downloaded: {output_path.name}")
            return output_path
            
        except requests.HTTPError as e:
            logger.error(f"HTTP error downloading {url}: {e}")
            self._record_failure(url, str(e), metadata)
            raise
        except requests.ConnectionError as e:
            logger.error(f"Connection error downloading {url}: {e}")
            self._record_failure(url, str(e), metadata)
            raise
        except requests.Timeout as e:
            logger.error(f"Timeout downloading {url}: {e}")
            self._record_failure(url, str(e), metadata)
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {url}: {e}")
            self._record_failure(url, str(e), metadata)
            raise
    
    def _record_failure(self, url: str, error: str, metadata: Optional[Dict] = None) -> None:
        """
        Record a failed download.
        
        Args:
            url: URL that failed
            error: Error message
            metadata: Optional metadata
        """
        failure_record = {
            'url': url,
            'error': error,
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata,
        }
        self.failed_downloads.append(failure_record)
    
    def batch_download(
        self,
        urls: List[str],
        metadata: Optional[Dict] = None,
        max_workers: int = MAX_WORKERS,
        skip_existing: bool = True,
        organize: bool = True,
        progress_callback: Optional[Callable] = None,
    ) -> Dict[str, List[Path]]:
        """
        Download multiple PDFs concurrently.
        
        Args:
            urls: List of PDF URLs to download
            metadata: Optional metadata dictionary (categorized links)
            max_workers: Maximum number of concurrent downloads
            skip_existing: Skip files that already exist
            organize: Organize files by year/subject
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with 'successful' and 'failed' lists
        
        Example:
            >>> downloader = PDFDownloader()
            >>> result = downloader.batch_download(pdf_links, max_workers=5)
            >>> print(f"Downloaded: {len(result['successful'])}")
        """
        logger.info(f"Starting batch download of {len(urls)} files with {max_workers} workers")
        
        successful: List[Path] = []
        failed: List[str] = []
        
        # Prepare metadata lookup
        metadata_lookup = {}
        if metadata and 'all' in metadata:
            for item in metadata['all']:
                metadata_lookup[item['url']] = item
        
        # Download with thread pool and progress bar
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_url = {}
            for url in urls:
                item_metadata = metadata_lookup.get(url)
                future = executor.submit(
                    self.download_pdf,
                    url,
                    metadata=item_metadata,
                    skip_existing=skip_existing,
                    organize=organize,
                )
                future_to_url[future] = url
            
            # Process completed tasks with progress bar
            with tqdm(total=len(urls), desc="Downloading PDFs", unit="file") as pbar:
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        if result is not None:
                            successful.append(result)
                            pbar.set_postfix(
                                success=len(successful),
                                failed=len(failed),
                                refresh=False
                            )
                        else:
                            failed.append(url)
                    except Exception as e:
                        logger.error(f"Failed to download {url}: {e}")
                        failed.append(url)
                    
                    pbar.update(1)
                    
                    if progress_callback:
                        progress_callback(len(successful), len(failed), len(urls))
        
        logger.info(
            f"Batch download complete: {len(successful)} successful, "
            f"{len(failed)} failed out of {len(urls)} total"
        )
        
        return {
            'successful': successful,
            'failed': failed,
        }
    
    def save_metadata(self, filepath: Path = METADATA_FILE) -> None:
        """
        Save download history to JSON file.
        
        Args:
            filepath: Path to save metadata
        """
        ensure_directory(filepath.parent)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.download_history, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved metadata for {len(self.download_history)} downloads to {filepath}")
    
    def save_failed_downloads(self, filepath: Path = FAILED_DOWNLOADS_FILE) -> None:
        """
        Save failed downloads to JSON file.
        
        Args:
            filepath: Path to save failed downloads
        """
        if not self.failed_downloads:
            logger.info("No failed downloads to save")
            return
        
        ensure_directory(filepath.parent)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.failed_downloads, f, indent=2, ensure_ascii=False)
        
        logger.warning(f"Saved {len(self.failed_downloads)} failed downloads to {filepath}")
    
    def get_statistics(self) -> Dict:
        """
        Get download statistics.
        
        Returns:
            Dictionary with statistics
        """
        total_size = sum(record['size'] for record in self.download_history)
        
        stats = {
            'total_downloads': len(self.download_history),
            'total_failures': len(self.failed_downloads),
            'total_size': total_size,
            'total_size_formatted': format_bytes(total_size),
            'by_year': {},
            'by_subject': {},
        }
        
        for record in self.download_history:
            metadata = record.get('metadata', {})
            
            year = metadata.get('year')
            if year:
                stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
            
            subject = metadata.get('subject')
            if subject:
                stats['by_subject'][subject] = stats['by_subject'].get(subject, 0) + 1
        
        return stats
    
    def print_statistics(self) -> None:
        """
        Print download statistics.
        """
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("DOWNLOAD STATISTICS")
        print("="*60)
        print(f"\nTotal downloads: {stats['total_downloads']}")
        print(f"Total failures: {stats['total_failures']}")
        print(f"Total size: {stats['total_size_formatted']}")
        
        if stats['by_year']:
            print(f"\nDownloads by year:")
            for year, count in sorted(stats['by_year'].items(), reverse=True):
                print(f"  - {year}: {count} files")
        
        if stats['by_subject']:
            print(f"\nDownloads by subject:")
            for subject, count in sorted(stats['by_subject'].items()):
                print(f"  - {subject}: {count} files")
        
        print("\n" + "="*60 + "\n")
    
    def close(self) -> None:
        """
        Close the HTTP session.
        """
        self.session.close()
        logger.debug("HTTP session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

