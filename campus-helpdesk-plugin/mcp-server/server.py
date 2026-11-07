#!/usr/bin/env python3
"""
Campus Helpdesk MCP Server
A lightweight Model Context Protocol (MCP) server over stdio built using the official Python 'mcp' SDK.

Exposes:
- Tool: get_timetable(batch: str, day: str)
- Tool: get_fee_status(student_id: str)
- Resource: hostel_rules (URI: hostel://rules)
"""

import csv
import json
from pathlib import Path
import re
from typing import Dict, List, Optional, Tuple

# Official MCP SDK server import (compatible with mcp 2.x and mcp 1.x)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP  # type: ignore

# Initialize the MCP Server instance
mcp = FastMCP("campus-helpdesk-mcp")

# Candidate relative paths to locate timetable.csv dynamically
POTENTIAL_CSV_PATHS = [
    # 1. When server.py is bundled inside campus-helpdesk-plugin/mcp-server/
    Path(__file__).resolve().parent.parent / "skills" / "timetable-helper" / "data" / "timetable.csv",
    # 2. When server.py is at repo root mcp-server/
    Path(__file__).resolve().parent.parent / "campus-helpdesk-plugin" / "skills" / "timetable-helper" / "data" / "timetable.csv",
    # 3. Direct relative paths from current working directory
    Path("campus-helpdesk-plugin/skills/timetable-helper/data/timetable.csv").resolve(),
    Path("skills/timetable-helper/data/timetable.csv").resolve(),
]

# Embedded mock fallback data for Semester 3 Section A (strictly labeled as mock fallback)
FALLBACK_RECORDS: List[Dict[str, str]] = [
    {"day": "Monday", "start_time": "09:00", "end_time": "10:00", "subject": "Data Structures", "faculty": "Dr. Sharma", "room": "Lab 301", "semester": "3", "section": "A"},
    {"day": "Monday", "start_time": "10:00", "end_time": "11:00", "subject": "Database Management Systems", "faculty": "Prof. Mehta", "room": "Room 204", "semester": "3", "section": "A"},
    {"day": "Monday", "start_time": "11:15", "end_time": "12:15", "subject": "Operating Systems", "faculty": "Dr. Rao", "room": "Room 205", "semester": "3", "section": "A"},
    {"day": "Tuesday", "start_time": "09:00", "end_time": "10:00", "subject": "Computer Networks", "faculty": "Prof. Shah", "room": "Room 202", "semester": "3", "section": "A"},
    {"day": "Tuesday", "start_time": "10:00", "end_time": "11:00", "subject": "Data Structures", "faculty": "Dr. Sharma", "room": "Lab 301", "semester": "3", "section": "A"},
    {"day": "Tuesday", "start_time": "11:15", "end_time": "12:15", "subject": "Mathematics", "faculty": "Prof. Patil", "room": "Room 203", "semester": "3", "section": "A"},
    {"day": "Wednesday", "start_time": "09:00", "end_time": "10:00", "subject": "Operating Systems", "faculty": "Dr. Rao", "room": "Room 205", "semester": "3", "section": "A"},
    {"day": "Wednesday", "start_time": "10:00", "end_time": "11:00", "subject": "Computer Networks", "faculty": "Prof. Shah", "room": "Room 202", "semester": "3", "section": "A"},
    {"day": "Wednesday", "start_time": "11:15", "end_time": "12:15", "subject": "Database Management Systems", "faculty": "Prof. Mehta", "room": "Room 204", "semester": "3", "section": "A"},
    {"day": "Thursday", "start_time": "09:00", "end_time": "10:00", "subject": "Mathematics", "faculty": "Prof. Patil", "room": "Room 203", "semester": "3", "section": "A"},
    {"day": "Thursday", "start_time": "10:00", "end_time": "11:00", "subject": "Data Structures", "faculty": "Dr. Sharma", "room": "Lab 301", "semester": "3", "section": "A"},
    {"day": "Thursday", "start_time": "11:15", "end_time": "12:15", "subject": "Computer Networks", "faculty": "Prof. Shah", "room": "Room 202", "semester": "3", "section": "A"},
    {"day": "Friday", "start_time": "09:00", "end_time": "10:00", "subject": "Database Management Systems", "faculty": "Prof. Mehta", "room": "Room 204", "semester": "3", "section": "A"},
    {"day": "Friday", "start_time": "10:00", "end_time": "11:00", "subject": "Operating Systems", "faculty": "Dr. Rao", "room": "Room 205", "semester": "3", "section": "A"},
    {"day": "Friday", "start_time": "11:15", "end_time": "12:15", "subject": "Mathematics", "faculty": "Prof. Patil", "room": "Room 203", "semester": "3", "section": "A"},
]

# Synthetic mock fee database for academic assignment demonstration only
MOCK_FEE_DATABASE: Dict[str, Dict[str, str]] = {
    "STU1001": {
        "student_id": "STU1001",
        "student_name": "Aarav Sharma (Mock Student)",
        "batch": "Semester 3, Section A",
        "status": "Paid",
        "amount_due": "$0.00",
        "last_payment_date": "2026-08-15",
        "receipt_number": "REC-2026-8812",
        "is_mock_data": "true",
    },
    "STU1002": {
        "student_id": "STU1002",
        "student_name": "Ananya Patel (Mock Student)",
        "batch": "Semester 3, Section A",
        "status": "Pending",
        "amount_due": "$1,250.00",
        "due_date": "2026-11-20",
        "notice": "Tuition installment due before end of month",
        "is_mock_data": "true",
    },
    "STU1003": {
        "student_id": "STU1003",
        "student_name": "Rohan Iyer (Mock Student)",
        "batch": "Semester 3, Section A",
        "status": "Overdue",
        "amount_due": "$2,500.00",
        "due_date": "2026-10-31",
        "notice": "Late fee of $50 applied. Please contact Accounts Office.",
        "is_mock_data": "true",
    },
    "STU1004": {
        "student_id": "STU1004",
        "student_name": "Sneha Kulkarni (Mock Student)",
        "batch": "Semester 3, Section A",
        "status": "Paid",
        "amount_due": "$0.00",
        "last_payment_date": "2026-08-10",
        "receipt_number": "REC-2026-7941",
        "is_mock_data": "true",
    },
    "STU1005": {
        "student_id": "STU1005",
        "student_name": "Vikram Singh (Mock Student)",
        "batch": "Semester 3, Section A",
        "status": "Pending",
        "amount_due": "$600.00",
        "due_date": "2026-11-25",
        "notice": "Laboratory maintenance fee pending",
        "is_mock_data": "true",
    },
}

# Synthetic hostel rules markdown document (clearly identified as coursework mock data)
HOSTEL_RULES_CONTENT = """# Campus Hostel Rules and Regulations (Coursework Mock Data)

> NOTE: This document contains synthetic policies and fictional contact information for coursework testing only. It does not represent verified university policy.

### 1. Curfew & Gate Timings
- Main hostel entry gates close at **10:00 PM** on weekdays (Monday - Friday) and **10:30 PM** on weekends (Saturday - Sunday).
- Late returns require prior written permission from the Chief Hostel Warden.
- Night-out requests must be logged through the Campus Student Portal at least 24 hours in advance.

### 2. Quiet Hours & Discipline
- Mandatory quiet study hours are observed daily from **11:00 PM to 06:00 AM**.
- High-volume speakers, disruptive musical instruments, or loud group gatherings in corridors are strictly prohibited.

### 3. Visitor Policy
- Outside visitors, parents, and day-scholars are permitted only in the ground-floor visitor lounge between **09:00 AM and 07:00 PM**.
- Visitors are strictly prohibited from entering dormitory rooms or living corridors at any time.

### 4. Safety and Electrical Appliances
- Heavy electrical appliances exceeding 500W (immersion water heaters, induction cooktops, room heaters) are not permitted.
- Possession or consumption of alcohol, tobacco products, or illicit substances is strictly prohibited.

### 5. Emergency Contacts (Mock / Fictional)
- **Hostel Warden Desk**: Ext. 401 | +91-00000-00401 (Mock Contact)
- **Campus Security Control Room**: Ext. 100 | +91-00000-00100 (Mock Contact)
- **Campus Health Clinic & Ambulance**: Ext. 108 | +91-00000-00108 (Mock Contact)
"""

VALID_WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
WEEKEND_DAYS = ["Saturday", "Sunday"]


def _load_timetable_data() -> Tuple[List[Dict[str, str]], str]:
    """Load records from timetable.csv if available; otherwise return fallback records.

    Returns:
        A tuple of (records, source_type) where source_type is 'csv' or 'fallback_mock'.
    """
    for candidate in POTENTIAL_CSV_PATHS:
        if candidate.exists():
            try:
                with open(candidate, mode="r", encoding="utf-8-sig") as f:
                    reader = csv.DictReader(f)
                    records = [dict(row) for row in reader]
                    if records and "subject" in records[0]:
                        return records, "csv"
            except Exception:
                pass
    return list(FALLBACK_RECORDS), "fallback_mock"


def _parse_batch(batch: str) -> Tuple[Optional[str], Optional[str]]:
    """Parse semester and section from user batch query string.

    Examples:
        'Semester 3, Section A' -> ('3', 'A')
        'Semester 3, Section B' -> ('3', 'B')
        'Sem 3A' -> ('3', 'A')
        '3-A' -> ('3', 'A')
        'Semester 3' -> ('3', None)
        'Section B' -> (None, 'B')
    """
    clean = batch.strip().lower()

    # Match combined patterns like '3a', '3-a', 'sem 3a', 'sem 3-a'
    m_comb = re.search(r'\b(?:sem|semester)?\s*([0-9]+)\s*[-_/\s,]?\s*(?:sec|section)?\s*([a-zA-Z])\b', clean)
    if m_comb:
        return m_comb.group(1), m_comb.group(2).upper()

    # Explicit semester pattern
    sem = None
    m_sem = re.search(r'\b(?:sem|semester)\s*([0-9]+)\b', clean)
    if m_sem:
        sem = m_sem.group(1)
    elif re.search(r'\b([0-9]+)\b', clean):
        sem = re.search(r'\b([0-9]+)\b', clean).group(1)

    # Explicit section pattern
    sec = None
    m_sec = re.search(r'\b(?:sec|section)\s*([a-zA-Z])\b', clean)
    if m_sec:
        sec = m_sec.group(1).upper()

    return sem, sec


@mcp.tool()
def get_timetable(batch: str, day: str) -> str:
    """Retrieve the class timetable schedule for a given batch and day.

    Args:
        batch: The student cohort or batch identifier (e.g. 'Semester 3, Section A', 'Sem 3A', '3-A').
        day: The day of the week to query (e.g. 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday').

    Returns:
        A JSON string containing the matching schedule records, or a structured not-found error message.
    """
    clean_day = day.strip().capitalize()
    records, data_source = _load_timetable_data()

    # 1. Validate Day
    if clean_day in WEEKEND_DAYS:
        return json.dumps(
            {
                "status": "empty",
                "batch": batch,
                "day": clean_day,
                "data_source": data_source,
                "message": f"No scheduled classes found for {clean_day}. Classes run Monday through Friday.",
                "records": [],
            },
            indent=2,
        )

    if clean_day not in VALID_WEEKDAYS:
        return json.dumps(
            {
                "status": "error",
                "batch": batch,
                "day": day,
                "data_source": data_source,
                "message": f"Invalid day '{day}'. Allowed values: {', '.join(VALID_WEEKDAYS)}.",
                "records": [],
            },
            indent=2,
        )

    # 2. Explicitly Parse and Validate Batch (Semester & Section)
    sem, sec = _parse_batch(batch)

    # Validate semester: only Semester 3 is present in the verified dataset
    if sem is not None and sem != "3":
        return json.dumps(
            {
                "status": "not_found",
                "batch": batch,
                "day": clean_day,
                "data_source": data_source,
                "message": f"No timetable data found for semester '{sem}'. Available mock dataset covers Semester 3, Section A only.",
                "records": [],
            },
            indent=2,
        )

    # Validate section: only Section A is present in the verified dataset
    # Critical Bug Fix: Never return Section A records for a Section B (or other non-A) query!
    if sec is not None and sec != "A":
        return json.dumps(
            {
                "status": "not_found",
                "batch": batch,
                "day": clean_day,
                "data_source": data_source,
                "message": f"No timetable data found for section '{sec}'. Available mock dataset covers Semester 3, Section A only.",
                "records": [],
            },
            indent=2,
        )

    # 3. Filter Dataset by explicit Semester ('3'), Section ('A'), and Day
    target_sem = "3"
    target_sec = "A"

    matching = [
        r for r in records
        if r.get("day", "").strip().lower() == clean_day.lower()
        and r.get("semester", "").strip() == target_sem
        and r.get("section", "").strip().upper() == target_sec
    ]

    response_payload = {
        "status": "success" if matching else "empty",
        "batch": f"Semester {target_sem}, Section {target_sec}",
        "day": clean_day,
        "data_source": data_source,
        "count": len(matching),
        "records": matching,
    }

    if data_source == "fallback_mock":
        response_payload["warning"] = "Data loaded from embedded mock fallback records because timetable.csv was not accessible."

    return json.dumps(response_payload, indent=2)


@mcp.tool()
def get_fee_status(student_id: str) -> str:
    """Look up the academic fee payment status for a student by their Student ID.

    Args:
        student_id: The unique student identifier (e.g. 'STU1001', 'STU1002', 'STU1003', 'STU1004', 'STU1005').

    Returns:
        A JSON string with the fee status (Paid, Pending, Overdue) and balance details.
    """
    clean_id = student_id.strip().upper()

    if clean_id in MOCK_FEE_DATABASE:
        return json.dumps(
            {
                "status": "success",
                "record": MOCK_FEE_DATABASE[clean_id],
                "is_mock_data": True,
                "note": "Synthetic academic fee data for coursework assignment testing.",
            },
            indent=2,
        )

    return json.dumps(
        {
            "status": "not_found",
            "message": f"No fee record found for student ID '{student_id}'.",
            "sample_ids": list(MOCK_FEE_DATABASE.keys()),
            "is_mock_data": True,
        },
        indent=2,
    )


@mcp.resource("hostel://rules")
def hostel_rules() -> str:
    """Returns the official campus hostel rules, gate curfews, quiet hours, and safety policies."""
    return HOSTEL_RULES_CONTENT


if __name__ == "__main__":
    # Runs the MCP server over standard input/output (stdio)
    mcp.run(transport="stdio")
