#!/usr/bin/env python3
"""
test_skill.py
Comprehensive automated test suite for the timetable-helper skill.

Verifies:
1. Normal timetable queries (by weekday).
2. Subject-based searches.
3. Explicit semester and section filtering (Semester 3, Section A).
4. Invalid day handling (e.g. 'Funday' -> exit code 1).
5. Unsupported semester handling (e.g. Semester 4 -> empty results).
6. Unsupported section handling (e.g. Section B -> empty results).
7. Structured JSON output format (--json).
8. Listing utilities (--list-subjects and --list-days).
9. Missing CSV file error handling (exit code 2).
10. Data integrity & anti-tamper check (SHA-256 hash remains unchanged).
"""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parent
LOOKUP_SCRIPT = (
    REPO_ROOT
    / "campus-helpdesk-plugin"
    / "skills"
    / "timetable-helper"
    / "scripts"
    / "timetable_lookup.py"
)
DATASET_PATH = (
    REPO_ROOT
    / "campus-helpdesk-plugin"
    / "skills"
    / "timetable-helper"
    / "data"
    / "timetable.csv"
)


def compute_file_sha256(filepath: Path) -> str:
    """Calculate SHA-256 checksum of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        hasher.update(f.read())
    return hasher.hexdigest()


class TestTimetableSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.initial_hash = compute_file_sha256(DATASET_PATH)

    def tearDown(self):
        # Ensure timetable.csv was not modified in any test
        current_hash = compute_file_sha256(DATASET_PATH)
        self.assertEqual(
            self.initial_hash,
            current_hash,
            "Critical Error: timetable.csv checksum changed during test execution!",
        )

    def run_lookup(self, args: list) -> subprocess.CompletedProcess:
        """Run the lookup script with python3."""
        cmd = [sys.executable, str(LOOKUP_SCRIPT)] + args
        return subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

    def test_01_query_valid_day_monday(self):
        """Query Monday schedule: should return 3 records (Data Structures, DBMS, OS)."""
        res = self.run_lookup(["--day", "Monday", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 3)
        subjects = [r["subject"] for r in data["records"]]
        self.assertIn("Data Structures", subjects)
        self.assertIn("Database Management Systems", subjects)
        self.assertIn("Operating Systems", subjects)

    def test_02_query_all_supported_days(self):
        """Query Tuesday through Friday to ensure all weekdays return records."""
        for day in ["Tuesday", "Wednesday", "Thursday", "Friday"]:
            res = self.run_lookup(["--day", day, "--json"])
            self.assertEqual(res.returncode, 0, f"Failed for {day}")
            data = json.loads(res.stdout)
            self.assertEqual(data["status"], "success")
            self.assertEqual(data["count"], 3, f"Expected 3 classes for {day}")

    def test_03_query_by_subject(self):
        """Query by subject 'Data Structures'."""
        res = self.run_lookup(["--subject", "Data Structures", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 3)
        for r in data["records"]:
            self.assertEqual(r["subject"], "Data Structures")
            self.assertEqual(r["room"], "Lab 301")
            self.assertEqual(r["faculty"], "Dr. Sharma")

    def test_04_query_valid_semester_and_section(self):
        """Query Semester 3, Section A on Wednesday."""
        res = self.run_lookup(
            ["--day", "Wednesday", "--semester", "3", "--section", "A", "--json"]
        )
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["count"], 3)

    def test_05_invalid_day(self):
        """Query with invalid day 'Funday': should return exit code 1."""
        res = self.run_lookup(["--day", "Funday", "--json"])
        self.assertEqual(res.returncode, 1)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "error")
        self.assertIn("Invalid day 'Funday'", data["message"])

    def test_06_unsupported_semester(self):
        """Query unsupported semester 4: should return 0 records (empty status)."""
        res = self.run_lookup(["--semester", "4", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "empty")
        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["records"]), 0)

    def test_07_unsupported_section_b(self):
        """Query Section B: should return 0 records since dataset only has Section A."""
        res = self.run_lookup(["--section", "B", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "empty")
        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["records"]), 0)

    def test_08_unknown_subject(self):
        """Query non-existent subject 'Quantum Physics'."""
        res = self.run_lookup(["--subject", "Quantum Physics", "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "empty")
        self.assertEqual(data["count"], 0)

    def test_09_list_subjects_and_days(self):
        """Test --list-subjects and --list-days discovery utilities."""
        res_subj = self.run_lookup(["--list-subjects", "--json"])
        self.assertEqual(res_subj.returncode, 0)
        data_subj = json.loads(res_subj.stdout)
        self.assertIn("Data Structures", data_subj["subjects"])
        self.assertIn("Computer Networks", data_subj["subjects"])

        res_days = self.run_lookup(["--list-days", "--json"])
        self.assertEqual(res_days.returncode, 0)
        data_days = json.loads(res_days.stdout)
        self.assertEqual(
            data_days["days"],
            ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
        )

    def test_10_missing_csv_file_error(self):
        """Test handling when CSV file does not exist (exit code 2)."""
        res = self.run_lookup(["--csv-path", "/non/existent/path/timetable.csv", "--json"])
        self.assertEqual(res.returncode, 2)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "error")
        self.assertIn("not found", data["message"].lower())

    def test_11_adversarial_tamper_attempt(self):
        """Test adversarial attempt: trying to pass malicious filter or fake subjects."""
        malicious_input = "'; DROP TABLE timetable; --"
        res = self.run_lookup(["--subject", malicious_input, "--json"])
        self.assertEqual(res.returncode, 0)
        data = json.loads(res.stdout)
        self.assertEqual(data["status"], "empty")
        # Ensure the file was not modified
        self.assertEqual(compute_file_sha256(DATASET_PATH), self.initial_hash)


if __name__ == "__main__":
    unittest.main(verbosity=2)
