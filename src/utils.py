"""
Utility functions for DNB Annales Scraper.

This module provides common utility functions including:
- Logging configuration
- File management
- Rate limiting
- Filename sanitization
"""

import time
import re
from pathlib import Path
from typing import Optional, Callable, Any
from functools import wraps
from loguru import logger
import sys

from config.settings import (
    LOGS_DIR,
    LOG_LEVEL,
    LOG_FORMAT,
    LOG_ROTATION,
    LOG_RETENTION,
    REQUEST_DELAY,
)


def setup_logging(log_file: Optional[str] = None) -> None:
    """
    Configure logging for the application.
    
    Args:
        log_file: Optional custom log file name. If None, uses default naming.
    
    Returns:
        None
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger with colors
    logger.add(
        sys.stderr,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        colorize=True,
    )
    
    # Add file logger with rotation
    if log_file is None:
        log_file = LOGS_DIR / "dnb_scraper_{time:YYYY-MM-DD}.log"
    else:
        log_file = LOGS_DIR / log_file
    
    logger.add(
        log_file,
        format=LOG_FORMAT,
        level=LOG_LEVEL,
        rotation=LOG_ROTATION,
        retention=LOG_RETENTION,
        compression="zip",
    )
    
    logger.info("Logging initialized")


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize a filename by removing invalid characters.
    
    Args:
        filename: The original filename
        max_length: Maximum length for the filename (default: 255)
    
    Returns:
        Sanitized filename safe for filesystem use
    
    Example:
        >>> sanitize_filename("Sujet : Maths 2023.pdf")
        'Sujet_Maths_2023.pdf'
    """
    # Remove or replace invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Replace multiple spaces/underscores with single underscore
    filename = re.sub(r'[\s_]+', '_', filename)
    
    # Remove leading/trailing spaces and underscores
    filename = filename.strip('_ ')
    
    # Ensure it doesn't exceed max length
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        max_name_length = max_length - len(ext) - 1
        filename = f"{name[:max_name_length]}.{ext}" if ext else name[:max_length]
    
    return filename


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, create if it doesn't.
    
    Args:
        path: Path to the directory
    
    Returns:
        The path object
    """
    path.mkdir(parents=True, exist_ok=True)
    return path


def format_bytes(bytes_size: int) -> str:
    """
    Format bytes into human-readable format.
    
    Args:
        bytes_size: Size in bytes
    
    Returns:
        Formatted string (e.g., "1.23 MB")
    
    Example:
        >>> format_bytes(1536)
        '1.50 KB'
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"


class RateLimiter:
    """
    Rate limiter to control request frequency.
    
    This class ensures that requests are spaced out according to
    a specified delay, respecting the target server.
    
    Example:
        >>> limiter = RateLimiter(delay=1.5)
        >>> limiter.wait()  # Waits if necessary
    """
    
    def __init__(self, delay: float = REQUEST_DELAY):
        """
        Initialize the rate limiter.
        
        Args:
            delay: Minimum delay between requests in seconds
        """
        self.delay = delay
        self.last_request_time: Optional[float] = None
    
    def wait(self) -> None:
        """
        Wait if necessary to maintain the rate limit.
        
        Returns:
            None
        """
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.delay:
                sleep_time = self.delay - elapsed
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
                time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def reset(self) -> None:
        """
        Reset the rate limiter.
        
        Returns:
            None
        """
        self.last_request_time = None


def rate_limited(delay: float = REQUEST_DELAY) -> Callable:
    """
    Decorator to apply rate limiting to a function.
    
    Args:
        delay: Minimum delay between function calls in seconds
    
    Returns:
        Decorated function
    
    Example:
        >>> @rate_limited(delay=2.0)
        ... def fetch_page(url):
        ...     return requests.get(url)
    """
    limiter = RateLimiter(delay)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            limiter.wait()
            return func(*args, **kwargs)
        return wrapper
    return decorator


def retry_on_failure(
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff
        exceptions: Tuple of exceptions to catch
    
    Returns:
        Decorated function
    
    Example:
        >>> @retry_on_failure(max_retries=3, backoff_factor=2.0)
        ... def download_file(url):
        ...     return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    
                    wait_time = backoff_factor ** attempt
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator


def create_directory_structure(base_path: Path, year: Optional[str] = None, 
                               subject: Optional[str] = None) -> Path:
    """
    Create organized directory structure for downloaded files.
    
    Args:
        base_path: Base directory path
        year: Optional year for organization
        subject: Optional subject for organization
    
    Returns:
        Path to the created directory
    
    Example:
        >>> create_directory_structure(Path("data"), year="2023", subject="Maths")
        Path('data/2023/Maths')
    """
    path = base_path
    
    if year:
        path = path / year
    
    if subject:
        path = path / subject
    
    return ensure_directory(path)


def get_file_extension(url: str, filename: Optional[str] = None) -> str:
    """
    Extract file extension from URL or filename.
    
    Args:
        url: URL string
        filename: Optional filename (if known)
    
    Returns:
        File extension with leading dot (e.g., '.pdf', '.zip')
        Returns '.pdf' as default if no extension found
    
    Example:
        >>> get_file_extension("https://example.com/docs/file.pdf")
        '.pdf'
        >>> get_file_extension("https://example.com/archive.zip")
        '.zip'
    """
    from urllib.parse import urlparse, unquote
    from pathlib import Path
    
    # Try filename first if provided
    if filename:
        ext = Path(filename).suffix
        if ext:
            return ext.lower()
    
    # Try URL path
    parsed = urlparse(url)
    path_filename = unquote(parsed.path.split('/')[-1])
    if path_filename and '.' in path_filename:
        ext = Path(path_filename).suffix
        if ext:
            return ext.lower()
    
    # Default to .pdf
    return '.pdf'


def extract_filename_from_url(url: str) -> str:
    """
    Extract filename from URL.
    
    Args:
        url: URL string
    
    Returns:
        Extracted filename
    
    Example:
        >>> extract_filename_from_url("https://example.com/docs/file.pdf")
        'file.pdf'
    """
    from urllib.parse import urlparse, unquote
    
    parsed = urlparse(url)
    filename = unquote(parsed.path.split('/')[-1])
    
    # Fallback if no filename found
    if not filename or '.' not in filename:
        filename = "downloaded_file.pdf"
    
    return sanitize_filename(filename)

