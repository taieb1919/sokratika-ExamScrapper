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


def main_logic(args: argparse.Namespace) -> None:
    """
    Main logic for scraping, validation, and downloading.
    
    Args:
        args: Command line arguments
    """
    logger.info("Scraping and summarizing available PDFs")

    with DNBScraper(base_url=args.url) as scraper:
        pdf_links = scraper.extract_pdf_links(max_pages=args.pages)
        summary = scraper.get_summary_dict()

        # Print summary
        print("\n" + "=" * 60)
        print("DNB SCRAPER SUMMARY")
        print("=" * 60)
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
        print("\n" + "=" * 60 + "\n")

        # Validation control
        validation_ok = True
        if getattr(args, 'validate', False):
            try:
                run_validation(args, scraper)
            except SystemExit as e:
                validation_ok = (e.code == 0)
                if not getattr(args, 'download', False):
                    # If only validate was requested, re-raise to exit with the same code
                    raise

        # Download logic
        if getattr(args, 'download', False):
            if getattr(args, 'validate', False) and not validation_ok:
                logger.error("Validation failed; aborting download as requested")
                return
            if not pdf_links:
                logger.warning("No PDFs to download")
                return

            # Prepare download inputs from structured_entries
            urls = []
            metadata_list = []
            for entry in scraper.structured_entries:
                for f in entry.files:
                    urls.append(f.download_url)
                    metadata_list.append({
                        'url': f.download_url,
                        'filename': f.filename_for_save + '.pdf',
                        'file_id': f.file_id,
                        'year': entry.session.value.split('_')[0] if '_' in entry.session.value else None,
                        'subject': entry.discipline.value,
                        'session': entry.session.value,
                        'series': entry.serie.value,
                        'is_correction': False,
                        'document_type': 'sujet',
                    })
            metadata = {'all': metadata_list}

            output_dir = RAW_DATA_DIR
            max_workers = MAX_WORKERS

            with PDFDownloader(output_dir=output_dir) as downloader:
                logger.info(f"Downloading to: {output_dir}")
                results = downloader.batch_download(
                    urls=urls,
                    metadata=metadata,
                    max_workers=max_workers,
                    skip_existing=True,
                    organize=True,
                )
                downloader.print_statistics()
                downloader.save_metadata()
                if results['failed']:
                    downloader.save_failed_downloads()
                    logger.warning(f"{len(results['failed'])} downloads failed")
                logger.success(
                    f"Download complete: {len(results['successful'])} successful, {len(results['failed'])} failed"
                )


def run_validation(args: argparse.Namespace, scraper: Optional[DNBScraper] = None) -> None:
    """
    Validate structured entries per row and generate a CSV report.
    - For each ExamEntry: session, discipline, serie, localisation must not be None; files >= 1.
    - Output columns: ID, Session, Discipline, Serie, Localisation, Files_Count, Status (OK/MISSING)
    - Exit 1 if any MISSING.
    """
    import csv
    from sys import exit as sys_exit

    rows = []
    missing = False

    # Ensure we have structured entries available
    if scraper is None:
        with DNBScraper(base_url=args.url) as s:
            s.extract_pdf_links(max_pages=args.pages)
            entries = getattr(s, 'structured_entries', [])
    else:
        # Reuse entries from provided scraper
        entries = getattr(scraper, 'structured_entries', [])

    # Build CSV rows per File
    for entry in entries:
        files_count = len(entry.files)
        for f in entry.files:
            status = 'OK'
            if not (f.file_id and f.filename and f.filename_for_save and f.download_url):
                status = 'MISSING'
                missing = True

            rows.append({
                'ID': entry.id,
                'IDFile': f.file_id or '',
                'Session': entry.session.value if entry.session else '',
                'Discipline': entry.discipline.value if entry.discipline else '',
                'Serie': entry.serie.value if entry.serie else '',
                'Localisation': entry.localisation.value if entry.localisation else '',
                'Files_Count': files_count,
                'Status': status,
                'FileName': f.filename or '',
                'FileNameToSave': f.filename_for_save or '',
                'Link': f.download_url or '',
            })

    # Write CSV
    report_path = Path('validation_report.csv')
    with open(report_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(
            f,
            fieldnames=['ID', 'IDFile', 'Session', 'Discipline', 'Serie', 'Localisation', 'Files_Count', 'Status', 'FileName', 'FileNameToSave', 'Link']
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"Validation report written to {report_path.resolve()}")
    if missing:
        sys_exit(1)
    else:
        sys_exit(0)
def main():
    """
    Main function with CLI argument parsing.
    """
    parser = argparse.ArgumentParser(
        description="DNB Annales Scraper - Unified CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape and print summary (no validation, no download)
  python main.py

  # Validate only (writes validation_report.csv and exits with code)
  python main.py --validate -p 1

  # Download regardless of validation warnings
  python main.py --download -p 2

  # Validate first, then download only if OK
  python main.py --validate --download
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
    
    # Simplified flags
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate entries and generate validation_report.csv'
    )
    parser.add_argument(
        '--download',
        action='store_true',
        help='Download PDFs after scraping (see validation rules)'
    )
    parser.add_argument(
        '--pages', '-p',
        type=int,
        default=None,
        help='Limit the number of pages to scrape (default: all)'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    # Setup logging
    import os
    os.environ['LOG_LEVEL'] = args.log_level
    setup_logging(log_file=args.log_file)
    
    # Single entry point
    main_logic(args)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.warning("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)
