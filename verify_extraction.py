"""
Verify extraction completeness by comparing extracted files against tar archives.
Generates JSON and Markdown reports showing item counts per year.
"""

import json
import tarfile
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List
import sys


@dataclass
class YearVerification:
    year: int
    tar_pdf_count: int = 0
    tar_json_count: int = 0
    tar_total_files: int = 0
    extracted_pdf_count: int = 0
    extracted_json_count: int = 0
    extracted_total_files: int = 0
    pdf_match: bool = False
    json_match: bool = False
    total_match: bool = False
    pdf_diff: int = 0
    json_diff: int = 0
    total_diff: int = 0


def count_files_in_tar(tar_path: Path) -> tuple[int, int, int]:
    """Count PDF and JSON files in a tar archive."""
    pdf_count = 0
    json_count = 0
    try:
        with tarfile.open(tar_path, "r") as tar:
            for member in tar.getmembers():
                if member.isfile():
                    name = member.name.lower()
                    if name.endswith(".pdf"):
                        pdf_count += 1
                    elif name.endswith(".json"):
                        json_count += 1
    except Exception as e:
        print(f"Error reading {tar_path}: {e}")
        return 0, 0, 0
    return pdf_count, json_count, pdf_count + json_count


def count_files_in_directory(dir_path: Path) -> tuple[int, int, int]:
    """Count PDF and JSON files in a directory (recursively)."""
    pdf_count = 0
    json_count = 0
    try:
        for file_path in dir_path.rglob("*"):
            if file_path.is_file():
                name = file_path.name.lower()
                if name.endswith(".pdf"):
                    pdf_count += 1
                elif name.endswith(".json"):
                    json_count += 1
    except Exception as e:
        print(f"Error reading directory {dir_path}: {e}")
        return 0, 0, 0
    return pdf_count, json_count, pdf_count + json_count


def verify_year(year: int, data_dir: Path, extracted_base_dir: Path) -> YearVerification:
    """Verify a single year's extraction against its tar archives."""
    result = YearVerification(year=year)

    # Check main tar archive (contains PDFs)
    tar_file = data_dir / f"{year}.tar"
    metadata_tar = data_dir / f"{year}_metadata.tar"

    if tar_file.exists():
        pdf_count, _, total = count_files_in_tar(tar_file)
        result.tar_pdf_count = pdf_count
        result.tar_total_files += total
    else:
        print(f"Warning: {tar_file} not found")

    # Check metadata tar (contains JSONs)
    if metadata_tar.exists():
        _, json_count, total = count_files_in_tar(metadata_tar)
        result.tar_json_count = json_count
        result.tar_total_files += total
    else:
        print(f"Warning: {metadata_tar} not found")

    # Check extracted directory
    extracted_dir = extracted_base_dir / str(year)
    if extracted_dir.exists():
        pdf_count, json_count, total = count_files_in_directory(extracted_dir)
        result.extracted_pdf_count = pdf_count
        result.extracted_json_count = json_count
        result.extracted_total_files = total
    else:
        print(f"Warning: Extracted directory {extracted_dir} not found")

    # Calculate differences
    result.pdf_diff = result.extracted_pdf_count - result.tar_pdf_count
    result.json_diff = result.extracted_json_count - result.tar_json_count
    result.total_diff = result.extracted_total_files - result.tar_total_files

    # Determine matches
    result.pdf_match = result.pdf_diff == 0
    result.json_match = result.json_diff == 0
    result.total_match = result.total_diff == 0

    return result


def generate_json_report(results: List[YearVerification], output_path: Path) -> None:
    """Generate JSON report."""
    report = {
        "summary": {
            "total_years": len(results),
            "years_with_pdf_mismatch": sum(1 for r in results if not r.pdf_match),
            "years_with_json_mismatch": sum(1 for r in results if not r.json_match),
            "years_with_total_mismatch": sum(1 for r in results if not r.total_match),
            "total_tar_pdfs": sum(r.tar_pdf_count for r in results),
            "total_tar_jsons": sum(r.tar_json_count for r in results),
            "total_extracted_pdfs": sum(r.extracted_pdf_count for r in results),
            "total_extracted_jsons": sum(r.extracted_json_count for r in results),
            "total_pdf_diff": sum(r.pdf_diff for r in results),
            "total_json_diff": sum(r.json_diff for r in results),
        },
        "years": [asdict(r) for r in results],
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print(f"JSON report saved to: {output_path}")


def generate_markdown_report(results: List[YearVerification], output_path: Path) -> None:
    """Generate Markdown report."""
    summary = {
        "total_years": len(results),
        "years_with_pdf_mismatch": sum(1 for r in results if not r.pdf_match),
        "years_with_json_mismatch": sum(1 for r in results if not r.json_match),
        "years_with_total_mismatch": sum(1 for r in results if not r.total_match),
        "total_tar_pdfs": sum(r.tar_pdf_count for r in results),
        "total_tar_jsons": sum(r.tar_json_count for r in results),
        "total_extracted_pdfs": sum(r.extracted_pdf_count for r in results),
        "total_extracted_jsons": sum(r.extracted_json_count for r in results),
        "total_pdf_diff": sum(r.pdf_diff for r in results),
        "total_json_diff": sum(r.json_diff for r in results),
    }

    lines = [
        "# Supreme Court Data Extraction Verification Report",
        "",
        "## Summary",
        "",
        f"- **Total Years Checked:** {summary['total_years']}",
        f"- **Years with PDF Mismatch:** {summary['years_with_pdf_mismatch']}",
        f"- **Years with JSON Mismatch:** {summary['years_with_json_mismatch']}",
        f"- **Years with Total Mismatch:** {summary['years_with_total_mismatch']}",
        "",
        "## Overall Counts",
        "",
        "| Type | Tar Archives | Extracted | Difference |",
        "|------|-------------|-----------|------------|",
        f"| PDFs | {summary['total_tar_pdfs']:,} | {summary['total_extracted_pdfs']:,} | {summary['total_pdf_diff']:+d} |",
        f"| JSONs | {summary['total_tar_jsons']:,} | {summary['total_extracted_jsons']:,} | {summary['total_json_diff']:+d} |",
        f"| **Total** | **{summary['total_tar_pdfs'] + summary['total_tar_jsons']:,}** | **{summary['total_extracted_pdfs'] + summary['total_extracted_jsons']:,}** | **{summary['total_pdf_diff'] + summary['total_json_diff']:+d}** |",
        "",
        "## Per-Year Details",
        "",
        "| Year | Tar PDFs | Ext PDFs | PDF Diff | Tar JSONs | Ext JSONs | JSON Diff | Status |",
        "|------|----------|----------|----------|-----------|-----------|-----------|--------|",
    ]

    for r in sorted(results, key=lambda x: x.year):
        status = "✅" if r.total_match else "❌"
        lines.append(
            f"| {r.year} | {r.tar_pdf_count:,} | {r.extracted_pdf_count:,} | {r.pdf_diff:+d} | "
            f"{r.tar_json_count:,} | {r.extracted_json_count:,} | {r.json_diff:+d} | {status} |"
        )

    lines.extend([
        "",
        "## Legend",
        "",
        "- **Tar PDFs/JSONs**: Files counted inside the `.tar` archive",
        "- **Ext PDFs/JSONs**: Files found in the extracted directory",
        "- **Diff**: Extracted count minus Tar count (+N means more extracted, -N means missing)",
        "- **Status**: ✅ = counts match, ❌ = mismatch detected",
        "",
    ])

    # Add mismatch details
    mismatches = [r for r in results if not r.total_match]
    if mismatches:
        lines.extend([
            "## Mismatches Detail",
            "",
        ])
        for r in mismatches:
            lines.extend([
                f"### Year {r.year}",
                "",
            ])
            if not r.pdf_match:
                lines.append(f"- **PDFs:** Tar has {r.tar_pdf_count:,}, Extracted has {r.extracted_pdf_count:,} (diff: {r.pdf_diff:+d})")
            if not r.json_match:
                lines.append(f"- **JSONs:** Tar has {r.tar_json_count:,}, Extracted has {r.extracted_json_count:,} (diff: {r.json_diff:+d})")
            lines.append("")
    else:
        lines.extend([
            "## Mismatches Detail",
            "",
            "**No mismatches found!** All years have matching counts.",
            "",
        ])

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Markdown report saved to: {output_path}")


def main():
    # Paths
    data_dir = Path("c:/Users/admin/indian-supreme-court-judgments/data")
    extracted_base_dir = Path("c:/Users/admin/Desktop/Supreme Court Data")
    output_dir = Path("c:/Users/admin/indian-supreme-court-judgments")

    # Years to check (2000-2025)
    years = list(range(2000, 2026))

    print(f"Verifying extraction for years {years[0]}-{years[-1]}")
    print(f"Data directory: {data_dir}")
    print(f"Extracted directory: {extracted_base_dir}")
    print()

    # Verify each year
    results: List[YearVerification] = []
    for year in years:
        print(f"Checking year {year}...", end=" ")
        result = verify_year(year, data_dir, extracted_base_dir)
        results.append(result)
        status = "✅" if result.total_match else "❌"
        print(f"PDFs: {result.tar_pdf_count}/{result.extracted_pdf_count}, JSONs: {result.tar_json_count}/{result.extracted_json_count} {status}")

    # Generate reports
    json_path = output_dir / "extraction_verification_report.json"
    md_path = output_dir / "extraction_verification_report.md"

    generate_json_report(results, json_path)
    generate_markdown_report(results, md_path)

    print()
    print("=" * 60)
    print("Verification Complete!")
    print("=" * 60)

    # Print summary
    total_tar = sum(r.tar_total_files for r in results)
    total_extracted = sum(r.extracted_total_files for r in results)
    total_diff = total_extracted - total_tar

    print(f"\nTotal files in tar archives: {total_tar:,}")
    print(f"Total files extracted: {total_extracted:,}")
    print(f"Difference: {total_diff:+d}")

    mismatched_years = [r.year for r in results if not r.total_match]
    if mismatched_years:
        print(f"\nYears with mismatches: {mismatched_years}")
    else:
        print("\n✅ All years verified successfully - no mismatches!")


if __name__ == "__main__":
    main()
