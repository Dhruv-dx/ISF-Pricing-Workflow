#!/usr/bin/env python3
"""
ISF Pricing Workflow

Runs the full pipeline in one go:
  1. inshape_pricing_formatter: CSV → single formatted TXT (all clubs)
  2. split_club_files: formatted TXT → one TXT per club in club_files_{date}/
  3. dynamic_pricing: club TXTs + ISF markdown source → updated ISF_locations_{date}/

Usage:
  python workflow.py
  python workflow.py --csv "ISS Pricing 01292026.csv" --isf-dir ISF_locations_22-01-26
  python workflow.py --date 31-01-26
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

# Project root (where this script lives)
PROJECT_DIR = Path(__file__).resolve().parent


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run full ISF pricing pipeline: CSV → formatted TXT → per-club TXTs → updated ISF markdown."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=PROJECT_DIR / "pricing files" / "ISS Pricing 02172026 (1).csv",
        help="Path to InShape pricing CSV (default: pricing files/ISS Pricing 01292026.csv in project dir)",
    )
    parser.add_argument(
        "--isf-dir",
        type=Path,
        default=PROJECT_DIR / "ISF_locations_18-02-26",
        help="Source directory of ISF markdown location files (default: ISF_locations_22-01-26)",
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="DD-MM-YY",
        help="Date suffix for generated folders/files (default: today). Example: 31-01-26",
    )
    parser.add_argument(
        "--skip-format",
        action="store_true",
        help="Skip step 1 (assume formatted TXT already exists)",
    )
    parser.add_argument(
        "--skip-split",
        action="store_true",
        help="Skip step 2 (assume club_files_* dir already exists). Implies --skip-format if you only have split files.",
    )
    parser.add_argument(
        "--skip-update",
        action="store_true",
        help="Skip step 3 (do not update ISF markdown)",
    )
    return parser.parse_args()


def step1_format(csv_path: Path, date_str: str) -> Path:
    """Run inshape_pricing_formatter: CSV → inshape_pricing_formatted_{date}.txt"""
    from inshape_pricing_formatter import InShapePricingFormatter

    formatter = InShapePricingFormatter()
    output_file = PROJECT_DIR / f"inshape_pricing_formatted_{date_str}.txt"

    print("[Step 1] InShape pricing formatter: CSV → formatted TXT")
    print(f"  CSV:    {csv_path}")
    print(f"  Output: {output_file}")

    if not csv_path.exists():
        print(f"  Error: CSV not found: {csv_path}")
        sys.exit(1)

    formatted = formatter.process_csv_file(str(csv_path))
    if formatted.startswith("Error"):
        print(f"  Error: {formatted}")
        sys.exit(1)

    formatter.save_output(formatted, str(output_file))
    print(f"  Done. Wrote {output_file}\n")
    return output_file


def step2_split(formatted_txt: Path, date_str: str) -> Path:
    """Run split_club_files: formatted TXT → club_files_{date}/"""
    from split_club_files import ClubFileSplitter

    output_dir = PROJECT_DIR / f"club_files_{date_str}"
    splitter = ClubFileSplitter(output_directory=str(output_dir))

    print("[Step 2] Split club files: one TXT per club")
    print(f"  Input:  {formatted_txt}")
    print(f"  Output: {output_dir}")

    if not formatted_txt.exists():
        print(f"  Error: Formatted file not found: {formatted_txt}")
        sys.exit(1)

    splitter.process_file(str(formatted_txt))
    print(f"  Done. Club files in {output_dir}\n")
    return output_dir


def step3_update(txt_dir: Path, md_dir: Path, date_str: str) -> Path:
    """Run dynamic_pricing: club TXTs + ISF MD → ISF_locations_{date}/"""
    from dynamic_pricing import run as dynamic_pricing_run

    updated_dir = PROJECT_DIR / f"ISF_locations_{date_str}"
    csv_file = PROJECT_DIR / "NFC_file.csv"

    print("[Step 3] Update ISF markdown with pricing")
    print(f"  Club TXTs: {txt_dir}")
    print(f"  ISF source: {md_dir}")
    print(f"  Output:     {updated_dir}")

    if not txt_dir.exists():
        print(f"  Error: Club files dir not found: {txt_dir}")
        sys.exit(1)
    if not md_dir.exists():
        print(f"  Error: ISF source dir not found: {md_dir}")
        sys.exit(1)

    dynamic_pricing_run(
        txt_dir=txt_dir,
        md_dir=md_dir,
        updated_dir=updated_dir,
        csv_file=csv_file if csv_file.exists() else None,
        project_dir=PROJECT_DIR,
    )
    print(f"  Done. Updated ISF files in {updated_dir}\n")
    return updated_dir


def main():
    args = parse_args()
    date_str = args.date or datetime.now().strftime("%d-%m-%y")

    print("=" * 60)
    print("ISF Pricing Workflow")
    print(f"  Date: {date_str}")
    print(f"  CSV:  {args.csv}")
    print(f"  ISF:  {args.isf_dir}")
    print("=" * 60)

    formatted_txt = PROJECT_DIR / f"inshape_pricing_formatted_{date_str}.txt"
    club_dir = PROJECT_DIR / f"club_files_{date_str}"

    if not args.skip_format:
        step1_format(args.csv, date_str)
    else:
        print("[Step 1] Skipped (--skip-format)")
        if not formatted_txt.exists() and not args.skip_split:
            print(f"  Warning: {formatted_txt} not found; step 2 may fail.\n")
        else:
            print()

    if not args.skip_split:
        step2_split(formatted_txt, date_str)
    else:
        print("[Step 2] Skipped (--skip-split)")
        if not club_dir.exists() and not args.skip_update:
            print(f"  Warning: {club_dir} not found; step 3 may fail.\n")
        else:
            print()

    if not args.skip_update:
        step3_update(club_dir, args.isf_dir, date_str)
    else:
        print("[Step 3] Skipped (--skip-update)\n")

    print("=" * 60)
    print("Workflow finished.")
    print("=" * 60)


if __name__ == "__main__":
    main()
