#!/usr/bin/env python3
"""
timetable_lookup.py
Small helper script to query student timetable data from the mock CSV dataset.

Features:
- Filtering by day, subject, semester, and section.
- Input validation (valid days of week, numeric semester, existing file).
- Clean formatted table, markdown, or JSON output.
- Safe handling of empty results and missing files.
- Treating CSV values as literal data strings (never evaluated or executed).
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

VALID_DAYS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]
DAY_ORDER = {day: idx for idx, day in enumerate(VALID_DAYS)}

REQUIRED_COLUMNS = [
    "day",
    "start_time",
    "end_time",
    "subject",
    "faculty",
    "room",
    "semester",
    "section",
]


def resolve_csv_path(custom_path: Optional[str] = None) -> Path:
    """Resolve the path to the timetable CSV file."""
    if custom_path:
        return Path(custom_path).resolve()

    # 1. Look relative to the script location (skills/timetable-helper/scripts/..)
    script_dir = Path(__file__).resolve().parent
    script_relative_path = script_dir.parent / "data" / "timetable.csv"
    if script_relative_path.exists():
        return script_relative_path

    # 2. Look relative to repository root with plugin path
    plugin_path = Path("campus-helpdesk-plugin/skills/timetable-helper/data/timetable.csv").resolve()
    if plugin_path.exists():
        return plugin_path

    # 3. Look relative to root standalone path
    standalone_path = Path("skills/timetable-helper/data/timetable.csv").resolve()
    if standalone_path.exists():
        return standalone_path

    # Fallback to script-relative path
    return script_relative_path


def load_timetable(csv_path: Path) -> Tuple[List[Dict[str, str]], Optional[str]]:
    """Load and validate the timetable CSV dataset.

    Returns:
        (records, error_message)
    """
    if not csv_path.exists():
        return [], f"Timetable dataset file not found at '{csv_path}'."

    try:
        with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return [], f"Timetable dataset at '{csv_path}' is empty or invalid."

            missing_cols = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
            if missing_cols:
                return [], (
                    f"Timetable dataset missing required columns: {', '.join(missing_cols)}. "
                    f"Expected: {', '.join(REQUIRED_COLUMNS)}"
                )

            records = []
            for row in reader:
                # Treat all content as literal stripped data
                sanitized_row = {k: (v.strip() if v else "") for k, v in row.items()}
                records.append(sanitized_row)

            return records, None
    except Exception as exc:
        return [], f"Failed to read timetable dataset: {exc}"


def validate_filters(
    day: Optional[str],
    subject: Optional[str],
    semester: Optional[str],
    section: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    """Validate query filter parameters.

    Returns:
        (normalized_day, error_message)
    """
    normalized_day = None
    if day:
        day_clean = day.strip().capitalize()
        # Find case-insensitive match in VALID_DAYS
        matched_day = next((d for d in VALID_DAYS if d.lower() == day.strip().lower()), None)
        if not matched_day:
            return None, (
                f"Invalid day '{day}'. Allowed values: {', '.join(VALID_DAYS)}."
            )
        normalized_day = matched_day

    if semester:
        sem_clean = semester.strip()
        if not sem_clean.isdigit() or int(sem_clean) <= 0:
            return None, f"Invalid semester '{semester}'. Semester must be a positive integer."

    return normalized_day, None


def filter_timetable(
    records: List[Dict[str, str]],
    day: Optional[str] = None,
    subject: Optional[str] = None,
    semester: Optional[str] = None,
    section: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Filter records by day, subject, semester, and section."""
    results = []
    subject_query = subject.strip().lower() if subject else None
    semester_query = semester.strip() if semester else None
    section_query = section.strip().lower() if section else None

    for row in records:
        if day and row.get("day", "").lower() != day.lower():
            continue
        if subject_query and subject_query not in row.get("subject", "").lower():
            continue
        if semester_query and row.get("semester", "") != semester_query:
            continue
        if section_query and row.get("section", "").lower() != section_query:
            continue
        results.append(row)

    # Sort results by day of week order and start time
    def sort_key(item: Dict[str, str]):
        day_idx = DAY_ORDER.get(item.get("day", ""), 999)
        start = item.get("start_time", "00:00")
        return (day_idx, start)

    results.sort(key=sort_key)
    return results


def format_table(records: List[Dict[str, str]]) -> str:
    """Format records into a clean text table."""
    if not records:
        return "No matching timetable records found."

    headers = ["Day", "Start", "End", "Subject", "Faculty", "Room", "Sem", "Sec"]
    keys = ["day", "start_time", "end_time", "subject", "faculty", "room", "semester", "section"]

    col_widths = {k: len(h) for k, h in zip(keys, headers)}
    for row in records:
        for k in keys:
            col_widths[k] = max(col_widths[k], len(str(row.get(k, ""))))

    # Build header row
    header_str = " | ".join(h.ljust(col_widths[k]) for k, h in zip(keys, headers))
    divider_str = "-+-".join("-" * col_widths[k] for k in keys)

    # Build data rows
    data_rows = []
    for row in records:
        data_rows.append(
            " | ".join(str(row.get(k, "")).ljust(col_widths[k]) for k in keys)
        )

    summary = f"\nTotal records found: {len(records)}"
    return f"{header_str}\n{divider_str}\n" + "\n".join(data_rows) + summary


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Query the student timetable CSV dataset safely without hallucinations."
    )
    parser.add_argument(
        "--day",
        "-d",
        type=str,
        help="Day of week (e.g. Monday, Tuesday, Wednesday, Thursday, Friday).",
    )
    parser.add_argument(
        "--subject",
        "-s",
        type=str,
        help="Subject name or substring (e.g. 'Data Structures', 'Networks').",
    )
    parser.add_argument(
        "--semester",
        "-sem",
        type=str,
        help="Semester number (e.g. 3).",
    )
    parser.add_argument(
        "--section",
        "-sec",
        type=str,
        help="Section letter (e.g. A).",
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        help="Optional path to custom timetable CSV file.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format.",
    )
    parser.add_argument(
        "--list-subjects",
        action="store_true",
        help="List all distinct subjects in the dataset.",
    )
    parser.add_argument(
        "--list-days",
        action="store_true",
        help="List all days having schedule entries in the dataset.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 1. Resolve CSV path
    csv_file = resolve_csv_path(args.csv_path)

    # 2. Load timetable
    records, load_err = load_timetable(csv_file)
    if load_err:
        if args.json:
            print(json.dumps({"status": "error", "message": load_err}, indent=2))
        else:
            print(f"Error: {load_err}", file=sys.stderr)
        return 2

    # 3. Handle utility listing flags
    if args.list_subjects:
        subjects = sorted({r.get("subject", "") for r in records if r.get("subject")})
        if args.json:
            print(json.dumps({"subjects": subjects}, indent=2))
        else:
            print("Available Subjects in Timetable:")
            for s in subjects:
                print(f" - {s}")
        return 0

    if args.list_days:
        days_in_data = sorted(
            {r.get("day", "") for r in records if r.get("day")},
            key=lambda d: DAY_ORDER.get(d, 999),
        )
        if args.json:
            print(json.dumps({"days": days_in_data}, indent=2))
        else:
            print("Days with Schedule Entries:")
            for d in days_in_data:
                print(f" - {d}")
        return 0

    # 4. Validate query filters
    normalized_day, val_err = validate_filters(
        day=args.day,
        subject=args.subject,
        semester=args.semester,
        section=args.section,
    )
    if val_err:
        if args.json:
            print(json.dumps({"status": "error", "message": val_err}, indent=2))
        else:
            print(f"Error: {val_err}", file=sys.stderr)
        return 1

    # 5. Filter records
    results = filter_timetable(
        records=records,
        day=normalized_day,
        subject=args.subject,
        semester=args.semester,
        section=args.section,
    )

    # 6. Format and output results
    if args.json:
        payload: Dict[str, Any] = {
            "status": "success" if results else "empty",
            "count": len(results),
            "filters": {
                "day": normalized_day,
                "subject": args.subject,
                "semester": args.semester,
                "section": args.section,
            },
            "records": results,
            "message": "Found matching records." if results else "No matching timetable records found.",
        }
        print(json.dumps(payload, indent=2))
    else:
        if not results:
            print("No matching timetable records found.")
        else:
            print(format_table(results))

    return 0


if __name__ == "__main__":
    sys.exit(main())

