import os
import sys
from pathlib import Path
import urllib.request
import urllib.error
import logging
import argparse
from datetime import datetime


def setup_logging(log_file):
    """Setup logging to both file and console."""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    file_handler = logging.FileHandler(log_file, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


def download_file(url, output_path):
    """Download a file from URL to output_path."""
    try:
        logging.info(f"Downloading: {url}")
        
        start_time = datetime.now()
        urllib.request.urlretrieve(url, output_path)
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        file_size = os.path.getsize(output_path) / (1024 * 1024)
        speed = file_size / duration if duration > 0 else 0
        
        success_msg = f"✓ Successfully downloaded: {output_path.name} ({file_size:.2f} MB in {duration:.1f}s, {speed:.2f} MB/s)"
        logging.info(success_msg)
        logging.info(f"File saved at: {output_path.absolute()}")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            error_msg = f"✗ File not found (404): {url}"
        else:
            error_msg = f"✗ HTTP Error {e.code}: {url}"
        logging.warning(error_msg)
        return False
    except Exception as e:
        error_msg = f"✗ Error downloading {url}: {e}"
        logging.error(error_msg, exc_info=True)
        return False


def download_year_archives(year, output_dir):
    """Download both english and metadata tar files for a given year."""
    base_url = "https://indian-supreme-court-judgments.s3.amazonaws.com"
    
    english_url = f"{base_url}/data/tar/year={year}/english/english.tar"
    metadata_url = f"{base_url}/metadata/tar/year={year}/metadata.tar"
    
    english_path = output_dir / f"{year}.tar"
    metadata_path = output_dir / f"{year}_metadata.tar"
    
    separator = f"\n{'='*60}"
    year_header = f"Year {year}"
    logging.info(separator.strip())
    logging.info(year_header)
    logging.info(f"{'='*60}")
    
    english_success = download_file(english_url, english_path)
    metadata_success = download_file(metadata_url, metadata_path)
    
    logging.info(f"Year {year} summary: English={'SUCCESS' if english_success else 'FAILED'}, Metadata={'SUCCESS' if metadata_success else 'FAILED'}")
    
    return english_success, metadata_success


def main():
    parser = argparse.ArgumentParser(
        description='Download Indian Supreme Court judgment archives from S3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python download_archives.py --year 2000              # Download only year 2000
  python download_archives.py --year 2020 --year 2021  # Download specific years
  python download_archives.py --start 2000 --end 2005  # Download range 2000-2005
  python download_archives.py                          # Download all years (2000-2025)
        '''
    )
    parser.add_argument('--year', type=int, action='append', help='Specific year(s) to download (can be used multiple times)')
    parser.add_argument('--start', type=int, help='Start year for range download')
    parser.add_argument('--end', type=int, help='End year for range download')
    
    args = parser.parse_args()
    
    if args.year:
        years_to_download = sorted(set(args.year))
    elif args.start or args.end:
        start_year = args.start if args.start else 2000
        end_year = args.end if args.end else 2025
        years_to_download = list(range(start_year, end_year + 1))
    else:
        years_to_download = list(range(2000, 2026))
    
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    
    log_file = output_dir / f"download_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    logger = setup_logging(log_file)
    
    start_time = datetime.now()
    
    if len(years_to_download) == 1:
        header = f"Downloading Supreme Court archives for year {years_to_download[0]}"
    else:
        header = f"Downloading Supreme Court archives for {len(years_to_download)} years: {min(years_to_download)}-{max(years_to_download)}"
    output_info = f"Output directory: {output_dir.absolute()}"
    log_info = f"Log file: {log_file.absolute()}"
    
    logging.info(header)
    logging.info(output_info)
    logging.info(log_info)
    logging.info(f"Years to download: {years_to_download}")
    logging.info(f"Download started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    stats = {
        "english_success": 0,
        "english_failed": 0,
        "metadata_success": 0,
        "metadata_failed": 0,
        "english_failed_years": [],
        "metadata_failed_years": [],
    }
    
    for year in years_to_download:
        english_success, metadata_success = download_year_archives(year, output_dir)
        
        if english_success:
            stats["english_success"] += 1
        else:
            stats["english_failed"] += 1
            stats["english_failed_years"].append(year)
            
        if metadata_success:
            stats["metadata_success"] += 1
        else:
            stats["metadata_failed"] += 1
            stats["metadata_failed_years"].append(year)
    
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    summary_separator = f"\n{'='*60}"
    summary_header = "Download Summary"
    
    logging.info(summary_separator.strip())
    logging.info(summary_header)
    logging.info(f"{'='*60}")
    
    english_summary = f"English archives: {stats['english_success']} succeeded, {stats['english_failed']} failed"
    metadata_summary = f"Metadata archives: {stats['metadata_success']} succeeded, {stats['metadata_failed']} failed"
    total_summary = f"Total files downloaded: {stats['english_success'] + stats['metadata_success']}"
    duration_summary = f"Total duration: {total_duration/60:.1f} minutes ({total_duration:.0f} seconds)"
    output_summary = f"\nAll files saved in: {output_dir.absolute()}"
    log_summary = f"Detailed log saved in: {log_file.absolute()}"
    
    logging.info(english_summary)
    logging.info(metadata_summary)
    logging.info(total_summary)
    logging.info(duration_summary)
    logging.info(output_summary.strip())
    logging.info(log_summary)
    
    if stats["english_failed_years"]:
        failed_english = f"English archives failed for years: {stats['english_failed_years']}"
        logging.warning(failed_english)
    
    if stats["metadata_failed_years"]:
        failed_metadata = f"Metadata archives failed for years: {stats['metadata_failed_years']}"
        logging.warning(failed_metadata)
    
    logging.info(f"Download completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
