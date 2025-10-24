"""
File downloader for DNB exam papers (supports all formats: PDF, ZIP, DOC, DOCX, etc.).

This module provides the FileDownloader class which handles:
- Downloading files of any format (PDF, ZIP, DOC, DOCX, ODT, etc.)
- Batch downloading with multi-threading
- File validation based on type
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
    detect_file_type_from_content,
    get_extension_from_content_type,
)
from src.parser import MetadataParser


class FileDownloader:
    """
    Universal file downloader with support for batch downloads and validation.
    
    This class handles downloading files of any format with features like:
    - Multi-threaded batch downloads
    - Automatic retries with exponential backoff
    - Format-specific validation (PDF, ZIP, DOC, DOCX, ODT, etc.)
    - Automatic ZIP extraction after download
    - Progress tracking
    - Metadata tracking
    
    Attributes:
        output_dir: Directory where files will be saved
        session: Requests session for HTTP connections
        parser: MetadataParser for organizing files
    
    Example:
        >>> downloader = FileDownloader(output_dir="data/raw")
        >>> downloader.download_file("https://example.com/file.pdf")
        >>> downloader.download_file("https://example.com/docs.zip")  # Auto-extracted
        >>> downloader.batch_download(file_links, max_workers=5)
    """
    
    def __init__(self, output_dir: Path = RAW_DATA_DIR):
        """
        Initialize the file downloader.
        
        Args:
            output_dir: Directory to save downloaded files
        """
        self.output_dir = Path(output_dir)
        ensure_directory(self.output_dir)
        
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        self.parser = MetadataParser()
        self.download_history: List[Dict] = []
        self.failed_downloads: List[Dict] = []
        
        logger.info(f"FileDownloader initialized with output_dir: {self.output_dir}")
    
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
        
        # Check minimum file size (100 bytes)
        if filepath.stat().st_size < 100:
            logger.warning(f"Existing file too small: {filepath}")
            return False
        
        # Quick validation
        if not self.validate_file(filepath):
            logger.warning(f"Existing file invalid: {filepath}")
            return False
        
        logger.debug(f"File already exists: {filepath}")
        return True
    
    def validate_file(self, filepath: Path) -> bool:
        """
        Validate that a downloaded file is valid based on its extension.
        
        Supports validation for:
        - PDF files (checks magic bytes)
        - ZIP archives (checks ZIP structure)
        - DOC/DOCX files (checks structure)
        - Other formats (basic size validation)
        
        Args:
            filepath: Path to the file
        
        Returns:
            True if valid file, False otherwise
        """
        import zipfile
        
        if not filepath.exists():
            logger.error(f"File does not exist: {filepath}")
            return False
        
        # Check minimum file size (100 bytes)
        if filepath.stat().st_size < 100:
            logger.warning(f"File too small (possibly corrupted): {filepath}")
            return False
        
        ext = filepath.suffix.lower()
        
        try:
            if ext == '.pdf':
                # Validate PDF header
                if filepath.stat().st_size < MIN_PDF_SIZE:
                    logger.warning(f"File too small to be a valid PDF: {filepath}")
                    return False
                
                with open(filepath, 'rb') as f:
                    header = f.read(len(PDF_MAGIC_BYTES))
                    if not header.startswith(PDF_MAGIC_BYTES):
                        logger.warning(f"Invalid PDF magic bytes: {filepath}")
                        return False
                
                logger.debug(f"PDF validation passed: {filepath}")
                return True
            
            elif ext == '.zip':
                # Validate ZIP archive
                is_valid = zipfile.is_zipfile(filepath)
                if is_valid:
                    logger.debug(f"ZIP validation passed: {filepath}")
                else:
                    logger.warning(f"Invalid ZIP file: {filepath}")
                return is_valid
            
            elif ext in ['.doc', '.docx', '.odt']:
                # DOCX and ODT are ZIP-based formats
                if ext in ['.docx', '.odt']:
                    is_valid = zipfile.is_zipfile(filepath)
                    if is_valid:
                        logger.debug(f"{ext.upper()} validation passed: {filepath}")
                    else:
                        logger.warning(f"Invalid {ext.upper()} file: {filepath}")
                    return is_valid
                else:
                    # DOC files: check minimum size
                    is_valid = filepath.stat().st_size > 1000
                    if is_valid:
                        logger.debug(f"DOC validation passed: {filepath}")
                    else:
                        logger.warning(f"DOC file too small: {filepath}")
                    return is_valid
            
            elif ext == '.bin':
                # Unknown binary file: only check size
                is_valid = filepath.stat().st_size > 100
                if is_valid:
                    logger.debug(f"Binary file validation passed (size check): {filepath}")
                else:
                    logger.warning(f"Binary file too small: {filepath}")
                return is_valid
            
            else:
                # Unknown file type: basic validation (existence + size)
                logger.debug(f"Unknown file type {ext}, basic validation only: {filepath}")
                return True
        
        except Exception as e:
            logger.error(f"Error validating file {filepath}: {e}")
            return False
    
    def validate_pdf(self, filepath: Path) -> bool:
        """
        Alias for validate_file() for backward compatibility.
        
        Args:
            filepath: Path to the file
        
        Returns:
            True if valid file, False otherwise
        """
        return self.validate_file(filepath)
    
    @retry_on_failure(
        max_retries=MAX_RETRIES,
        backoff_factor=RETRY_BACKOFF_FACTOR,
        exceptions=(requests.RequestException,)
    )
    @rate_limited()
    def download_file(
        self,
        url: str,
        output_path: Optional[Path] = None,
        metadata: Optional[Dict] = None,
        skip_existing: bool = True,
        organize: bool = True,
    ) -> Optional[Path]:
        """
        Download a single file (any format: PDF, ZIP, DOC, DOCX, etc.).
        
        Args:
            url: URL of the file to download
            output_path: Custom output path (optional)
            metadata: Metadata dictionary for the file
            skip_existing: Skip if file already exists
            organize: Organize files by year/subject
        
        Returns:
            Path to downloaded file, or None if failed/skipped
        
        Example:
            >>> downloader = FileDownloader()
            >>> path = downloader.download_file("https://example.com/file.pdf")
            >>> path = downloader.download_file("https://example.com/docs.zip")
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
            
            # Get file size and content type from headers
            total_size = int(response.headers.get('content-length', 0))
            content_type = response.headers.get('content-type', 'unknown')
            
            logger.debug(f"Downloading {content_type}: {output_path.suffix} ({format_bytes(total_size)})")
            
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
            
            # Detect actual file type and rename if necessary
            detected_extension = None
            
            # 1. Try to get extension from Content-Type header
            ext_from_content_type = get_extension_from_content_type(content_type)
            if ext_from_content_type:
                detected_extension = ext_from_content_type
                logger.debug(f"Extension from Content-Type: {detected_extension}")
            
            # 2. If Content-Type is generic/unknown, detect from magic bytes
            # Only use magic bytes if Content-Type was None (generic/unknown)
            if ext_from_content_type is None:
                try:
                    with open(output_path, 'rb') as f:
                        magic_bytes = f.read(8)
                    detected_extension, detected_mime = detect_file_type_from_content(magic_bytes)
                    logger.debug(f"Extension from magic bytes: {detected_extension} ({detected_mime})")
                except Exception as e:
                    logger.warning(f"Could not read file for magic bytes detection: {e}")
                    detected_extension = '.bin'
            
            # 3. Rename file if extension differs
            current_extension = output_path.suffix.lower()
            if detected_extension and detected_extension != current_extension:
                # Create new path with correct extension
                new_output_path = output_path.with_suffix(detected_extension)
                
                # Handle potential conflicts
                if new_output_path.exists() and new_output_path != output_path:
                    logger.warning(f"File already exists with correct extension: {new_output_path}")
                    output_path.unlink(missing_ok=True)
                    return new_output_path if self.validate_file(new_output_path) else None
                
                # Rename the file
                output_path.rename(new_output_path)
                logger.info(f"Renamed file to correct extension: {output_path.name} → {new_output_path.name}")
                output_path = new_output_path
            
            # Validate downloaded file
            if not self.validate_file(output_path):
                logger.error(f"Downloaded file is not valid: {output_path}")
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
            
            # Extract ZIP files automatically
            if output_path.suffix.lower() == '.zip':
                self.extract_zip_file(output_path)
            
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
        Download multiple files concurrently (any format).
        
        Args:
            urls: List of file URLs to download
            metadata: Optional metadata dictionary (categorized links)
            max_workers: Maximum number of concurrent downloads
            skip_existing: Skip files that already exist
            organize: Organize files by year/subject
            progress_callback: Optional callback for progress updates
        
        Returns:
            Dictionary with 'successful' and 'failed' lists
        
        Example:
            >>> downloader = FileDownloader()
            >>> result = downloader.batch_download(file_links, max_workers=5)
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
                    self.download_file,
                    url,
                    metadata=item_metadata,
                    skip_existing=skip_existing,
                    organize=organize,
                )
                future_to_url[future] = url
            
            # Process completed tasks with progress bar
            with tqdm(total=len(urls), desc="Downloading files", unit="file") as pbar:
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
            'by_file_type': {},
        }
        
        for record in self.download_history:
            metadata = record.get('metadata', {})
            
            year = metadata.get('year')
            if year:
                stats['by_year'][year] = stats['by_year'].get(year, 0) + 1
            
            subject = metadata.get('subject')
            if subject:
                stats['by_subject'][subject] = stats['by_subject'].get(subject, 0) + 1
            
            # Group by file type
            filepath = record.get('filepath', '')
            ext = Path(filepath).suffix.lower() or '.unknown'
            stats['by_file_type'][ext] = stats['by_file_type'].get(ext, 0) + 1
        
        return stats
    
    def print_statistics(self) -> None:
        """
        Print download statistics grouped by file type, year, and subject.
        """
        stats = self.get_statistics()
        
        print("\n" + "="*60)
        print("DOWNLOAD STATISTICS")
        print("="*60)
        print(f"\nTotal downloads: {stats['total_downloads']}")
        print(f"Total failures: {stats['total_failures']}")
        print(f"Total size: {stats['total_size_formatted']}")
        
        if stats['by_file_type']:
            print(f"\nDownloads by file type:")
            for ext, count in sorted(stats['by_file_type'].items()):
                print(f"  - {ext}: {count} files")
        
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
    
    def download_pdf(
        self,
        url: str,
        output_path: Optional[Path] = None,
        metadata: Optional[Dict] = None,
        skip_existing: bool = True,
        organize: bool = True,
    ) -> Optional[Path]:
        """
        Alias for download_file() for backward compatibility.
        
        Args:
            url: URL of the file to download
            output_path: Custom output path (optional)
            metadata: Metadata dictionary for the file
            skip_existing: Skip if file already exists
            organize: Organize files by year/subject
        
        Returns:
            Path to downloaded file, or None if failed/skipped
        """
        return self.download_file(url, output_path, metadata, skip_existing, organize)
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def extract_zip_file(self, zip_path: Path) -> Optional[Path]:
        """
        Extract ZIP file to folder with same name.
        
        Args:
            zip_path: Path to the ZIP file to extract
        
        Returns:
            Path to the extraction folder, or None if failed
        """
        import zipfile
        
        extract_folder = zip_path.parent / zip_path.stem
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_folder)
            logger.success(f"Extracted ZIP to: {extract_folder}")
            return extract_folder
        except Exception as e:
            logger.error(f"Failed to extract ZIP {zip_path}: {e}")
            return None
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()


# Alias for backward compatibility
PDFDownloader = FileDownloader

