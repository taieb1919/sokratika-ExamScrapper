"""
Metadata parser for DNB exam files.

This module provides functionality to extract and parse metadata
from data-atl-name attributes and PDF URLs.
"""

import re
from typing import Dict, Optional
from urllib.parse import unquote
from loguru import logger

from config.settings import SUBJECTS_MAP, SESSION_TYPES, SERIES_TYPES


class MetadataParser:
    """
    Parser for extracting metadata from DNB exam file data-atl-name attributes.
    
    This class analyzes data-atl-name attributes to extract structured information
    about exam papers, including year, subject, session, and series.
    
    The data-atl-name format is typically: "filename.pdf|file_id"
    Example: "24genfrdag1_v11.pdf|63414"
    
    Example:
        >>> parser = MetadataParser()
        >>> metadata = parser.parse_url("https://example.com/document/123/download", "24genfrdag1_v11.pdf|63414")
        >>> print(metadata['filename'])
        '24genfrdag1_v11.pdf'
    """
    
    def __init__(self):
        """Initialize the metadata parser."""
        self.subjects_map = SUBJECTS_MAP
        self.session_types = SESSION_TYPES
        self.series_types = SERIES_TYPES
    
    def parse_url(self, url: str, data_atl_name: Optional[str] = None) -> Dict[str, Optional[str]]:
        """
        Parse URL and data-atl-name to extract metadata.
        
        Args:
            url: The URL to parse (e.g., "/document/123/download")
            data_atl_name: The data-atl-name attribute (e.g., "24genfrdag1_v11.pdf|63414")
        
        Returns:
            Dictionary containing extracted metadata
        
        Example:
            >>> parser = MetadataParser()
            >>> parser.parse_url("/document/123/download", "24genfrdag1_v11.pdf|63414")
            {'url': '/document/123/download', 'filename': '24genfrdag1_v11.pdf', 'file_id': '63414', ...}
        """
        # Parse data-atl-name if provided
        filename = None
        file_id = None
        
        if data_atl_name:
            parts = data_atl_name.split('|')
            if len(parts) >= 1:
                filename = parts[0]
            if len(parts) >= 2:
                file_id = parts[1]
        
        # If no filename from data-atl-name, try to extract from URL
        if filename is None:
            filename = self._extract_filename_from_url(url)
        
        # Decode URL-encoded characters
        decoded_filename = unquote(filename) if filename else ""
        decoded_url = unquote(url)
        
        metadata = {
            'url': url,
            'filename': filename,
            'file_id': file_id,
            'year': self._extract_year(decoded_url, decoded_filename),
            'subject': self._extract_subject(decoded_url, decoded_filename),
            'session': self._extract_session(decoded_url, decoded_filename),
            'series': self._extract_series(decoded_url, decoded_filename),
            'is_correction': self._is_correction(decoded_url, decoded_filename),
            'document_type': self._extract_document_type(decoded_url, decoded_filename),
        }
        
        logger.debug(f"Parsed metadata for {filename}: {metadata}")
        return metadata
    
    def _extract_filename_from_url(self, url: str) -> str:
        """
        Extract filename from URL.
        
        Args:
            url: The URL
        
        Returns:
            Extracted filename
        """
        # For /document/*/download URLs, we can't extract a meaningful filename
        # Return a placeholder
        return url.split('/')[-1].split('?')[0] if '/' in url else url
    
    def _extract_year(self, url: str, filename: str) -> Optional[str]:
        """
        Extract year from URL or filename.
        
        Args:
            url: The URL
            filename: The filename
        
        Returns:
            Year as string (e.g., "2024") or None
        """
        text = f"{url} {filename}".lower()
        
        # Look for 2-digit year at the beginning (e.g., "24" for 2024)
        year_pattern_short = r'\b(2[0-4])\b'
        match = re.match(r'^(\d{2})', filename)
        if match:
            year_short = match.group(1)
            # Convert to full year (assume 20xx for DNB)
            return f"20{year_short}"
        
        # Look for 4-digit year (2000-2099)
        year_pattern = r'\b(20[0-2]\d)\b'
        match = re.search(year_pattern, text)
        if match:
            return match.group(1)
        
        return None
    
    def _extract_subject(self, url: str, filename: str) -> Optional[str]:
        """
        Extract subject from URL or filename.
        
        Args:
            url: The URL
            filename: The filename
        
        Returns:
            Standardized subject name or None
        """
        text = f"{url} {filename}".lower()
        
        # Try to match known subjects
        for key, subject in self.subjects_map.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(key) + r'\b'
            if re.search(pattern, text):
                logger.debug(f"Found subject: {subject} (matched: {key})")
                return subject
        
        # Special handling for combined subjects
        if re.search(r'\bhist(oire)?[-_]?geo(graphie)?\b', text):
            return "Histoire-Géographie"
        
        if re.search(r'\bphys(ique)?[-_]?chim(ie)?\b', text):
            return "Sciences (Physique-Chimie)"
        
        return None
    
    def _extract_session(self, url: str, filename: str) -> Optional[str]:
        """
        Extract session type from URL or filename.
        
        Args:
            url: The URL
            filename: The filename
        
        Returns:
            Session type (e.g., "normale", "remplacement") or None
        """
        text = f"{url} {filename}".lower()
        
        for session in self.session_types:
            pattern = r'\b' + re.escape(session) + r'\b'
            if re.search(pattern, text):
                return session
        
        # Check for month indicators
        if re.search(r'\bjuin\b', text):
            return "normale"
        if re.search(r'\bseptembre\b', text):
            return "remplacement"
        
        return None
    
    def _extract_series(self, url: str, filename: str) -> Optional[str]:
        """
        Extract series type from URL or filename.
        
        Args:
            url: The URL
            filename: The filename
        
        Returns:
            Series type (e.g., "generale", "professionnelle") or None
        """
        text = f"{url} {filename}".lower()
        
        # Check for professional series
        if re.search(r'\b(professionnelle|pro)\b', text):
            return "professionnelle"
        
        # Check for general series
        if re.search(r'\b(generale|gen)\b', text):
            return "generale"
        
        # Default to generale if not specified
        return "generale"
    
    def _is_correction(self, url: str, filename: str) -> bool:
        """
        Determine if the document is a correction/answer key.
        
        Args:
            url: The URL
            filename: The filename
        
        Returns:
            True if it's a correction, False otherwise
        """
        text = f"{url} {filename}".lower()
        
        correction_keywords = [
            'corrig', 'correction', 'corrige', 'reponses', 
            'solutions', 'answer', 'key'
        ]
        
        for keyword in correction_keywords:
            if keyword in text:
                return True
        
        return False
    
    def _extract_document_type(self, url: str, filename: str) -> str:
        """
        Determine the document type.
        
        Args:
            url: The URL
            filename: The filename
        
        Returns:
            Document type ("sujet" or "correction")
        """
        return "correction" if self._is_correction(url, filename) else "sujet"
    
    def generate_organized_filename(self, metadata: Dict) -> str:
        """
        Generate organized filename from metadata.
        
        Args:
            metadata: Metadata dictionary
        
        Returns:
            Sanitized filename with .pdf extension
        """
        # Use original filename if available
        if metadata.get('filename'):
            return metadata['filename']
        
        # Otherwise construct from metadata
        parts = []
        
        if metadata.get('year'):
            parts.append(metadata['year'])
        
        if metadata.get('subject'):
            subject = metadata['subject'].replace(' ', '_').replace('/', '_')
            parts.append(subject)
        
        if metadata.get('session'):
            parts.append(metadata['session'])
        
        if metadata.get('series'):
            parts.append(metadata['series'])
        
        doc_type = metadata.get('document_type', 'sujet')
        parts.append(doc_type)
        
        if metadata.get('file_id'):
            parts.append(metadata['file_id'])
        
        filename = '_'.join(parts) + '.pdf'
        
        # Sanitize (import from utils if needed)
        filename = filename.replace('é', 'e').replace('è', 'e')
        filename = filename.replace('à', 'a').replace('ô', 'o')
        
        return filename