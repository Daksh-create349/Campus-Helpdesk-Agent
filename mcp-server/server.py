#!/usr/bin/env python3
"""
Campus Helpdesk MCP Server
A minimal Model Context Protocol (MCP) server over stdio built using the official Python 'mcp' SDK.

Exposes:
- Tool: get_timetable(batch: str, day: str)
- Tool: get_fee_status(student_id: str)
- Resource: hostel_rules (URI: hostel://rules)
"""

import csv
import json
from pathlib import Path
from typing import Dict, List

# Official MCP SDK server import (compatible with mcp 2.x and mcp 1.x)
try:
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore
except (ImportError, ModuleNotFoundError):
    from mcp.server.fastmcp import FastMCP  # type: ignore

# Initialize the MCP Server instance
mcp = FastMCP("campus-helpdesk-mcp")

# Path to the mock timetable CSV file
TIMETABLE_CSV_PATH = (
    Path(__file__).resolve().parent.parent
    / "campus-helpdesk-plugin"
    / "skills"
    / "timetable-helper"
    / "data"
    / "timetable.csv"
)

# Embedded fallback data for Semester 3 Section A
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

# Sample mock fee status records
MOCK_FEE_DATABASE: Dict[str, Dict[str, str]] = {
    "STU1001": {
        "student_id": "STU1001",
        "student_name": "Aarav Sharma",
        "batch": "Semester 3, Section A",
        "status": "Paid",
        "amount_due": "$0.00",
        "last_payment_date": "2026-08-15",
        "receipt_number": "REC-2026-8812",
    },
    "STU1002": {
        "student_id": "STU1002",
        "student_name": "Ananya Patel",
        "batch": "Semester 3, Section A",
        "status": "Pending",
        "amount_due": "$1,250.00",
        "due_date": "2026-11-20",
        "notice": "Tuition installment due before end of month",
    },
    "STU1003": {
        "student_id": "STU1003",
        "student_name": "Rohan Iyer",
        "batch": "Semester 3, Section A",
        "status": "Overdue",
        "amount_due": "$2,500.00",
        "due_date": "2026-10-31",
        "notice": "Late fee of $50 applied. Please contact Accounts Office.",
    },
    "STU1004": {
        "student_id": "STU1004",
        "student_name": "Sneha Kulkarni",
        "batch": "Semester 3, Section A",
        "status": "Paid",
        "amount_due": "$0.00",
        "last_payment_date": "2026-08-10",
        "receipt_number": "REC-2026-7941",
    },
    "STU1005": {
        "student_id": "STU1005",
        "student_name": "Vikram Singh",
        "batch": "Semester 3, Section A",
        "status": "Pending",
        "amount_due": "$600.00",
        "due_date": "2026-11-25",
        "notice": "Laboratory maintenance fee pending",
    },
}

# Hostel rules markdown document
HOSTEL_RULES_CONTENT = """# Campus Hostel Rules and Regulations

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
- The possession or consumption of alcohol, tobacco products, and illicit substances is strictly prohibited on campus premises and will result in immediate suspension.

### 5. Emergency Contacts
- **Hostel Warden Desk**: Ext. 401 | +91-98765-43210
- **Campus Security Control Room**: Ext. 100 | +91-98765-11111
- **Campus Health Clinic & Ambulance**: Ext. 108 | +91-98765-22222
"""


def _load_timetable_data() -> List[Dict[str, str]]:
    """Load records from timetable.csv if available, otherwise return fallback records."""
    if TIMETABLE_CSV_PATH.exists():
        try:
            with open(TIMETABLE_CSV_PATH, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                return [dict(row) for row in reader]
        except Exception:
            pass
    return FALLBACK_RECORDS


@mcp.tool()
def get_timetable(batch: str, day: str) -> str:
    """Retrieve the class timetable schedule for a given batch and day.

    Args:
        batch: The student cohort or batch identifier (e.g. 'Semester 3, Section A', 'Sem 3A', '3-A').
        day: The day of the week to query (e.g. 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday').

    Returns:
        A JSON string containing the matching schedule records, or a not-found status message.
    """
    clean_day = day.strip().capitalize()
    records = _load_timetable_data()

    # The dataset specifically contains Semester 3, Section A records
    # Allow flexible matching for common user batch inputs (e.g. "3", "3A", "Semester 3", "Section A")
    clean_batch = batch.strip().lower()
    is_supported_batch = any(
        term in clean_batch for term in ["3", "sem 3", "semester 3", "section a", "3a", "3-a", "all", "default"]
    )

    if not is_supported_batch:
        return json.dumps(
            {
                "status": "not_found",
                "message": f"No timetable data found for batch '{batch}'. Available mock dataset covers Semester 3, Section A.",
                "records": [],
            },
            indent=2,
        )

    # Filter matching day
    matching = [r for r in records if r.get("day", "").strip().lower() == clean_day.lower()]

    if not matching:
        return json.dumps(
            {
                "status": "empty",
                "batch": "Semester 3, Section A",
                "day": clean_day,
                "message": f"No scheduled classes found for {clean_day}. Classes run Monday through Friday.",
                "records": [],
            },
            indent=2,
        )

    return json.dumps(
        {
            "status": "success",
            "batch": "Semester 3, Section A",
            "day": clean_day,
            "count": len(matching),
            "records": matching,
        },
        indent=2,
    )


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
            },
            indent=2,
        )

    return json.dumps(
        {
            "status": "not_found",
            "message": f"No fee record found for student ID '{student_id}'.",
            "sample_ids": list(MOCK_FEE_DATABASE.keys()),
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

# Updated by MCP workstream
