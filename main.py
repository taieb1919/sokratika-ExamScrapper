"""
Main entry point for DNB Annales Scraper.

This script provides a command-line interface for scraping and downloading
DNB exam papers from the French education website.
"""

import sys
import argparse
from pathlib import Path
from typing import Optional
from loguru import logger

from config.settings import BASE_URL, RAW_DATA_DIR, MAX_WORKERS
from src.scraper import DNBScraper
from src.downloader import PDFDownloader
from src.utils import setup_logging


def scrape_only(args: argparse.Namespace) -> None:
    """
    Scrape PDF links without downloading.
    
    Args:
        args: Command line arguments
    """
    logger.info("Starting scrape-only mode")
    
    with DNBScraper(base_url=args.url) as scraper:
        # Extract PDF links
        pdf_links = scraper.extract_pdf_links()
        logger.info(f"Found {len(pdf_links)} PDF links")
        
        # Get summary
        summary = scraper.get_summary_dict()
        
        # Print summary
        print("\n" + "="*60)
        print("DNB SCRAPER SUMMARY")
        print("="*60)
        print(f"\nTotal PDFs found: {summary['total']}")
        
        if summary['years']:
            print(f"\nAvailable years ({len(summary['years'])}):")
            for year in summary['years']:
                count = summary['by_year'].get(year, 0)
                print(f"  - {year}: {count} files")
        
        if summary['subjects']:
            print(f"\nAvailable subjects ({len(summary['subjects'])}):")
            for subject in summary['subjects']:
                count = summary['by_subject'].get(subject, 0)
                print(f"  - {subject}: {count} files")
        
        print(f"\nDocument types:")
        print(f"  - Sujets: {summary['by_type']['sujet']}")
        print(f"  - Corrections: {summary['by_type']['correction']}")
        print("\n" + "="*60 + "\n")
        
        # Save links to file if requested
        if args.output:
            output_file = Path(args.output)
            with open(output_file, 'w', encoding='utf-8') as f:
                for link_data in pdf_links:
                    # Write URL and data-atl-name
                    url = link_data['url']
                    data_atl_name = link_data.get('data_atl_name', '')
                    f.write(f"{url} | {data_atl_name}\n")
            logger.success(f"Saved {len(pdf_links)} links to {output_file}")


def download_pdfs(args: argparse.Namespace) -> None:
    """
    Scrape and download PDFs.
    
    Args:
        args: Command line arguments
    """
    logger.info("Starting scrape and download mode")
    
    # Scrape links
    with DNBScraper(base_url=args.url) as scraper:
        pdf_links = scraper.extract_pdf_links()
        logger.info(f"Found {len(pdf_links)} PDF links")
        
        # Get summary
        summary = scraper.get_summary_dict()
        
        # Print summary
        print("\n" + "="*60)
        print("DNB SCRAPER SUMMARY")
        print("="*60)
        print(f"\nTotal PDFs found: {summary['total']}")
        
        if summary['years']:
            print(f"\nAvailable years ({len(summary['years'])}):")
            for year in summary['years']:
                count = summary['by_year'].get(year, 0)
                print(f"  - {year}: {count} files")
        
        if summary['subjects']:
            print(f"\nAvailable subjects ({len(summary['subjects'])}):")
            for subject in summary['subjects']:
                count = summary['by_subject'].get(subject, 0)
                print(f"  - {subject}: {count} files")
        
        print("\n" + "="*60 + "\n")
    
    if not pdf_links:
        logger.warning("No PDFs to download")
        return
    
    # Download PDFs
    output_dir = Path(args.output_dir) if args.output_dir else RAW_DATA_DIR
    max_workers = args.workers if args.workers else MAX_WORKERS
    
    # Prepare URLs list for downloader (extract just the URLs)
    urls = [link_data['url'] for link_data in pdf_links]
    
    # Prepare metadata for downloader
    from src.parser import MetadataParser
    parser = MetadataParser()
    metadata = {
        'all': []
    }
    for link_data in pdf_links:
        meta = parser.parse_url(link_data['url'], link_data.get('data_atl_name'))
        metadata['all'].append(meta)
    
    with PDFDownloader(output_dir=output_dir) as downloader:
        logger.info(f"Downloading to: {output_dir}")
        
        results = downloader.batch_download(
            urls=urls,
            metadata=metadata,
            max_workers=max_workers,
            skip_existing=not args.force,
            organize=not args.no_organize,
        )
        
        # Print statistics
        downloader.print_statistics()
        
        # Save metadata
        downloader.save_metadata()
        
        # Save failed downloads if any
        if results['failed']:
            downloader.save_failed_downloads()
            logger.warning(f"{len(results['failed'])} downloads failed")
        
        logger.success(
            f"Download complete: {len(results['successful'])} successful, "
            f"{len(results['failed'])} failed"
        )


def list_available(args: argparse.Namespace) -> None:
    """
    List available years and subjects.
    
    Args:
        args: Command line arguments
    """
    logger.info("Listing available years and subjects")
    
    with DNBScraper(base_url=args.url) as scraper:
        pdf_links = scraper.extract_pdf_links()
        summary = scraper.get_summary_dict()
        
        years = summary['years']
        subjects = summary['subjects']
        
        print("\n" + "="*60)
        print("AVAILABLE YEARS:")
        print("="*60)
        for year in years:
            count = summary['by_year'].get(year, 0)
            print(f"  - {year}: {count} files")
        
        print("\n" + "="*60)
        print("AVAILABLE SUBJECTS:")
        print("="*60)
        for subject in subjects:
            count = summary['by_subject'].get(subject, 0)
            print(f"  - {subject}: {count} files")
        
        print("\n" + "="*60 + "\n")


def main():
    """
    Main function with CLI argument parsing.
    """
    parser = argparse.ArgumentParser(
        description="DNB Annales Scraper - Download exam papers from eduscol.education.fr",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape and download all PDFs
  python main.py download
  
  # Scrape only (no download)
  python main.py scrape --output links.txt
  
  # List available years and subjects
  python main.py list
  
  # Download with custom settings
  python main.py download --workers 10 --output-dir ./my_pdfs --force
        """
    )
    
    # Global arguments
    parser.add_argument(
        '--url',
        type=str,
        default=BASE_URL,
        help=f'URL to scrape (default: {BASE_URL})'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        type=str,
        help='Custom log file name (optional)'
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Scrape command
    scrape_parser = subparsers.add_parser(
        'scrape',
        help='Scrape PDF links without downloading'
    )
    scrape_parser.add_argument(
        '--output', '-o',
        type=str,
        help='Output file to save links'
    )
    
    # Download command
    download_parser = subparsers.add_parser(
        'download',
        help='Scrape and download PDFs'
    )
    download_parser.add_argument(
        '--output-dir', '-o',
        type=str,
        help=f'Output directory for PDFs (default: {RAW_DATA_DIR})'
    )
    download_parser.add_argument(
        '--workers', '-w',
        type=int,
        help=f'Number of concurrent downloads (default: {MAX_WORKERS})'
    )
    download_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Re-download existing files'
    )
    download_parser.add_argument(
        '--no-organize',
        action='store_true',
        help='Do not organize files by year/subject'
    )
    
    # List command
    list_parser = subparsers.add_parser(
        'list',
        help='List available years and subjects'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    import os
    os.environ['LOG_LEVEL'] = args.log_level
    setup_logging(log_file=args.log_file)
    
    # Execute command
    if args.command == 'scrape':
        scrape_only(args)
    elif args.command == 'download':
        download_pdfs(args)
    elif args.command == 'list':
        list_available(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
