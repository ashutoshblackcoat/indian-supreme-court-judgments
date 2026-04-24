"""
Verify that JSON and PDF files are properly paired in the extracted folders.
Checks that every JSON has a corresponding PDF and vice versa.
"""

import json
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Set, Tuple
import sys


@dataclass
class YearPairResult:
    year: int
    json_count: int = 0
    pdf_count: int = 0
    paired_count: int = 0
    orphaned_jsons: List[str] = None
    orphaned_pdfs: List[str] = None
    
    def __post_init__(self):
        if self.orphaned_jsons is None:
            self.orphaned_jsons = []
        if self.orphaned_pdfs is None:
            self.orphaned_pdfs = []
    
    @property
    def is_complete(self) -> bool:
        return len(self.orphaned_jsons) == 0 and len(self.orphaned_pdfs) == 0


def get_base_name(filename: str) -> str:
    """
    Extract the base name for pairing.
    - JSON: 2000_1_1_15.json -> 2000_1_1_15
    - PDF: 2000_1_1_15_EN.pdf -> 2000_1_1_15
    - Also handles S_ prefix: S_2000_1_1_15.json -> S_2000_1_1_15
    """
    # Remove extension
    if filename.endswith('.json'):
        base = filename[:-5]  # Remove .json
    elif filename.endswith('.pdf'):
        base = filename[:-4]  # Remove .pdf
        # Remove _EN suffix if present
        if base.endswith('_EN'):
            base = base[:-3]
    else:
        base = filename
    return base


def check_year_pairs(year: int, extracted_base_dir: Path) -> YearPairResult:
    """Check JSON/PDF pairing for a single year."""
    result = YearPairResult(year=year)
    year_dir = extracted_base_dir / str(year)
    
    if not year_dir.exists():
        print(f"Warning: Directory not found: {year_dir}")
        return result
    
    # Collect all JSON and PDF files
    json_files: Set[str] = set()
    pdf_files: Set[str] = set()
    json_to_original: Dict[str, str] = {}
    pdf_to_original: Dict[str, str] = {}
    
    for file_path in year_dir.iterdir():
        if file_path.is_file():
            filename = file_path.name
            base_name = get_base_name(filename)
            
            if filename.endswith('.json'):
                json_files.add(base_name)
                json_to_original[base_name] = filename
            elif filename.endswith('.pdf'):
                pdf_files.add(base_name)
                pdf_to_original[base_name] = filename
    
    result.json_count = len(json_files)
    result.pdf_count = len(pdf_files)
    
    # Find orphaned files
    json_without_pdf = json_files - pdf_files
    pdf_without_json = pdf_files - json_files
    
    result.orphaned_jsons = sorted([json_to_original[b] for b in json_without_pdf])
    result.orphaned_pdfs = sorted([pdf_to_original[b] for b in pdf_without_json])
    
    # Paired files
    paired = json_files & pdf_files
    result.paired_count = len(paired)
    
    return result


def generate_json_report(results: List[YearPairResult], output_path: Path) -> None:
    """Generate JSON report."""
    total_orphaned_jsons = sum(len(r.orphaned_jsons) for r in results)
    total_orphaned_pdfs = sum(len(r.orphaned_pdfs) for r in results)
    incomplete_years = [r.year for r in results if not r.is_complete]
    
    report = {
        "summary": {
            "total_years_checked": len(results),
            "complete_years": len(results) - len(incomplete_years),
            "incomplete_years": len(incomplete_years),
            "incomplete_year_list": incomplete_years,
            "total_json_files": sum(r.json_count for r in results),
            "total_pdf_files": sum(r.pdf_count for r in results),
            "total_paired_files": sum(r.paired_count for r in results),
            "total_orphaned_jsons": total_orphaned_jsons,
            "total_orphaned_pdfs": total_orphaned_pdfs,
            "all_pairs_complete": total_orphaned_jsons == 0 and total_orphaned_pdfs == 0
        },
        "years": [
            {
                "year": r.year,
                "json_count": r.json_count,
                "pdf_count": r.pdf_count,
                "paired_count": r.paired_count,
                "is_complete": r.is_complete,
                "orphaned_jsons": r.orphaned_jsons,
                "orphaned_pdfs": r.orphaned_pdfs,
                "orphaned_json_count": len(r.orphaned_jsons),
                "orphaned_pdf_count": len(r.orphaned_pdfs)
            }
            for r in results
        ]
    }
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    
    print(f"JSON report saved to: {output_path}")


def generate_markdown_report(results: List[YearPairResult], output_path: Path) -> None:
    """Generate Markdown report."""
    total_orphaned_jsons = sum(len(r.orphaned_jsons) for r in results)
    total_orphaned_pdfs = sum(len(r.orphaned_pdfs) for r in results)
    incomplete_years = [r.year for r in results if not r.is_complete]
    
    lines = [
        "# Filename Pair Verification Report",
        "",
        "## Summary",
        "",
        f"- **Total Years Checked:** {len(results)}",
        f"- **Complete Years:** {len(results) - len(incomplete_years)}",
        f"- **Years with Orphans:** {len(incomplete_years)}",
        "",
        "## Overall Counts",
        "",
        f"| Metric | Count |",
        f"|--------|-------|",
        f"| Total JSON Files | {sum(r.json_count for r in results):,} |",
        f"| Total PDF Files | {sum(r.pdf_count for r in results):,} |",
        f"| Paired Files | {sum(r.paired_count for r in results):,} |",
        f"| Orphaned JSONs | {total_orphaned_jsons:,} |",
        f"| Orphaned PDFs | {total_orphaned_pdfs:,} |",
        "",
    ]
    
    if not incomplete_years:
        lines.extend([
            "## ✅ All Files Properly Paired!",
            "",
            "Every JSON file has a corresponding PDF file and vice versa.",
            "",
        ])
    else:
        lines.extend([
            f"## ⚠️ Years with Orphaned Files: {incomplete_years}",
            "",
        ])
    
    # Per-year details
    lines.extend([
        "## Per-Year Details",
        "",
        "| Year | JSONs | PDFs | Paired | Orphaned JSONs | Orphaned PDFs | Status |",
        "|------|-------|------|--------|----------------|---------------|--------|",
    ])
    
    for r in sorted(results, key=lambda x: x.year):
        status = "✅" if r.is_complete else f"⚠️ ({len(r.orphaned_jsons)}J, {len(r.orphaned_pdfs)}P)"
        lines.append(
            f"| {r.year} | {r.json_count:,} | {r.pdf_count:,} | {r.paired_count:,} | "
            f"{len(r.orphaned_jsons)} | {len(r.orphaned_pdfs)} | {status} |"
        )
    
    # Detail section for orphaned files
    if incomplete_years:
        lines.extend([
            "",
            "## Orphaned Files Detail",
            "",
        ])
        
        for r in results:
            if not r.is_complete:
                lines.extend([
                    f"### Year {r.year}",
                    "",
                ])
                
                if r.orphaned_jsons:
                    lines.extend([
                        "**JSONs without matching PDFs:**",
                        "",
                    ])
                    for fname in r.orphaned_jsons[:20]:  # Limit to 20
                        lines.append(f"- `{fname}`")
                    if len(r.orphaned_jsons) > 20:
                        lines.append(f"- ... and {len(r.orphaned_jsons) - 20} more")
                    lines.append("")
                
                if r.orphaned_pdfs:
                    lines.extend([
                        "**PDFs without matching JSONs:**",
                        "",
                    ])
                    for fname in r.orphaned_pdfs[:20]:  # Limit to 20
                        lines.append(f"- `{fname}`")
                    if len(r.orphaned_pdfs) > 20:
                        lines.append(f"- ... and {len(r.orphaned_pdfs) - 20} more")
                    lines.append("")
    
    lines.extend([
        "",
        "## Filename Pattern",
        "",
        "Expected pairing:",
        "- JSON: `{year}_{volume}_{start}_{end}.json` or `S_{year}_{volume}_{start}_{end}.json`",
        "- PDF: `{year}_{volume}_{start}_{end}_EN.pdf` or `S_{year}_{volume}_{start}_{end}_EN.pdf`",
        "",
        "The base name (everything before `.json` or `_EN.pdf`) must match for pairing.",
        "",
    ])
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"Markdown report saved to: {output_path}")


def main():
    # Paths
    extracted_base_dir = Path("c:/Users/admin/Desktop/Supreme Court Data")
    output_dir = Path("c:/Users/admin/indian-supreme-court-judgments")
    
    # Years to check (2000-2025)
    years = list(range(2000, 2026))
    
    print(f"Verifying JSON/PDF pairs for years {years[0]}-{years[-1]}")
    print(f"Extracted directory: {extracted_base_dir}")
    print()
    
    # Check each year
    results: List[YearPairResult] = []
    for year in years:
        print(f"Checking year {year}...", end=" ")
        result = check_year_pairs(year, extracted_base_dir)
        results.append(result)
        
        if result.is_complete:
            print(f"✅ All {result.paired_count:,} files paired")
        else:
            print(f"⚠️ {len(result.orphaned_jsons)} orphaned JSONs, {len(result.orphaned_pdfs)} orphaned PDFs")
    
    # Generate reports
    json_path = output_dir / "filename_pair_verification_report.json"
    md_path = output_dir / "filename_pair_verification_report.md"
    
    generate_json_report(results, json_path)
    generate_markdown_report(results, md_path)
    
    print()
    print("=" * 60)
    print("Verification Complete!")
    print("=" * 60)
    
    # Print summary
    total_orphaned_jsons = sum(len(r.orphaned_jsons) for r in results)
    total_orphaned_pdfs = sum(len(r.orphaned_pdfs) for r in results)
    incomplete_years = [r.year for r in results if not r.is_complete]
    
    print(f"\nTotal JSON files: {sum(r.json_count for r in results):,}")
    print(f"Total PDF files: {sum(r.pdf_count for r in results):,}")
    print(f"Paired files: {sum(r.paired_count for r in results):,}")
    
    if total_orphaned_jsons == 0 and total_orphaned_pdfs == 0:
        print("\n✅ All files are properly paired!")
    else:
        print(f"\n⚠️ Orphaned JSONs: {total_orphaned_jsons}")
        print(f"⚠️ Orphaned PDFs: {total_orphaned_pdfs}")
        print(f"Years with issues: {incomplete_years}")


if __name__ == "__main__":
    main()
