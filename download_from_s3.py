"""
Download Indian Supreme Court Judgments from S3
No AWS credentials needed - bucket is public
"""

import boto3
from botocore import UNSIGNED
from botocore.client import Config
from pathlib import Path

# Create S3 client without credentials (for public bucket)
s3_client = boto3.client('s3', config=Config(signature_version=UNSIGNED))

BUCKET = "indian-supreme-court-judgments"
DOWNLOAD_DIR = Path("./downloaded_data")
DOWNLOAD_DIR.mkdir(exist_ok=True)

def download_year(year: int):
    """Download all data for a specific year"""
    print(f"Downloading data for year {year}...")
    
    files_to_download = [
        f"data/tar/year={year}/english/english.tar",
        f"data/tar/year={year}/regional/regional.tar",
        f"metadata/tar/year={year}/metadata.tar",
        f"metadata/parquet/year={year}/metadata.parquet",
    ]
    
    for s3_key in files_to_download:
        try:
            local_path = DOWNLOAD_DIR / Path(s3_key).name
            print(f"  Downloading {s3_key} -> {local_path}")
            s3_client.download_file(BUCKET, s3_key, str(local_path))
            print(f"  ✓ Downloaded {local_path}")
        except Exception as e:
            print(f"  ✗ Failed to download {s3_key}: {e}")

def list_available_years():
    """List all available years in the S3 bucket"""
    print("Listing available years...")
    response = s3_client.list_objects_v2(
        Bucket=BUCKET,
        Prefix="data/tar/",
        Delimiter="/"
    )
    
    years = []
    for prefix in response.get('CommonPrefixes', []):
        year = prefix['Prefix'].split('=')[1].rstrip('/')
        years.append(year)
    
    print(f"Available years: {', '.join(sorted(years))}")
    return sorted(years)

if __name__ == "__main__":
    # List available years
    list_available_years()
    
    # Download specific year (change as needed)
    year = 2024
    download_year(year)
