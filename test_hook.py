#!/usr/bin/env python3
"""
test_hook.py
Comprehensive automated test suite for the file-protection PreToolUse hook (block-writes.sh).

Tests:
1. Direct file write attempt (write_file / write_to_file on timetable.csv) -> DENY
2. File replacement attempt (edit_file / replace_file_content on timetable.csv) -> DENY
3. Multi-file replacement attempt (multi_replace_file_content on timetable.csv) -> DENY
4. Shell-based modification attempt (rm, >, truncate, sed -i on timetable.csv) -> DENY
5. Normal read operation (cat, timetable_lookup.py on timetable.csv) -> ALLOW
6. Unrelated file modification (write_file to notes.txt) -> ALLOW
7. Malformed hook input handling (invalid JSON / empty input) -> DENY (fail-safe)
"""

import json
from pathlib import Path
import subprocess
import sys
import unittest

REPO_ROOT = Path(__file__).resolve().parent
HOOK_SCRIPT = REPO_ROOT / "campus-helpdesk-plugin" / "hooks" / "block-writes.sh"


class TestBlockWritesHook(unittest.TestCase):
    def run_hook(self, payload_dict) -> dict:
        """Pipe payload JSON to block-writes.sh and parse stdout JSON response."""
        if isinstance(payload_dict, str):
            input_bytes = payload_dict
        else:
            input_bytes = json.dumps(payload_dict)

        proc = subprocess.run(
            ["bash", str(HOOK_SCRIPT)],
            input=input_bytes,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=str(REPO_ROOT / "campus-helpdesk-plugin"),
        )
        self.assertEqual(proc.returncode, 0, f"Hook failed with stderr: {proc.stderr}")
        try:
            return json.loads(proc.stdout.strip())
        except Exception as e:
            self.fail(f"Hook did not return valid JSON: '{proc.stdout}' - Error: {e}")

    def test_01_direct_file_write_attempt(self):
        """1. Direct file write attempt (write_file targeting timetable.csv) -> DENY."""
        payload = {
            "toolCall": {
                "name": "write_file",
                "args": {
                    "Path": "/Users/student/campus-helpdesk-plugin/skills/timetable-helper/data/timetable.csv",
                    "Content": "corrupted,data",
                },
            }
        }
        res = self.run_hook(payload)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("timetable.csv", res.get("reason", "").lower())

    def test_02_write_to_file_targetfile_argument(self):
        """1b. Direct file write attempt using write_to_file with TargetFile argument -> DENY."""
        payload = {
            "toolCall": {
                "name": "write_to_file",
                "args": {
                    "TargetFile": "skills/timetable-helper/data/timetable.csv",
                    "Content": "fake,class",
                },
            }
        }
        res = self.run_hook(payload)
        self.assertEqual(res.get("decision"), "deny")
        self.assertIn("timetable.csv", res.get("reason", "").lower())

    def test_03_file_replacement_attempt(self):
        """2. File replacement attempt (edit_file / replace_file_content) -> DENY."""
        payload_edit = {
            "toolCall": {
                "name": "edit_file",
                "args": {
                    "Path": "data/timetable.csv",
                    "Target": "Dr. Sharma",
                    "Replacement": "Dr. Hacker",
                },
            }
        }
        res_edit = self.run_hook(payload_edit)
        self.assertEqual(res_edit.get("decision"), "deny")

        payload_replace = {
            "toolCall": {
                "name": "replace_file_content",
                "args": {
                    "TargetFile": "campus-helpdesk-plugin/skills/timetable-helper/data/timetable.csv",
                    "Target": "09:00",
                    "Replacement": "12:00",
                },
            }
        }
        res_replace = self.run_hook(payload_replace)
        self.assertEqual(res_replace.get("decision"), "deny")

    def test_04_multi_file_replacement_attempt(self):
        """3. Multi-file replacement attempt (multi_replace_file_content) -> DENY."""
        payload = {
            "toolCall": {
                "name": "multi_replace_file_content",
                "args": {
                    "TargetFile": "skills/timetable-helper/data/timetable.csv",
                    "Replacements": [
                        {"Target": "Monday", "Replacement": "Sunday"}
                    ],
                },
            }
        }
        res = self.run_hook(payload)
        self.assertEqual(res.get("decision"), "deny")

    def test_05_shell_based_modification_attempts(self):
        """4. Shell-based modification attempts (rm, >, truncate, sed -i) -> DENY."""
        dangerous_commands = [
            "rm campus-helpdesk-plugin/skills/timetable-helper/data/timetable.csv",
            "rm -f data/timetable.csv",
            "echo 'hacked' > skills/timetable-helper/data/timetable.csv",
            "cat bad.csv >> data/timetable.csv",
            "truncate -s 0 data/timetable.csv",
            "sed -i 's/Sharma/Hacker/g' data/timetable.csv",
            "mv data/timetable.csv data/old.csv",
            "cp bad.csv data/timetable.csv",
        ]
        for cmd in dangerous_commands:
            payload = {
                "toolCall": {
                    "name": "run_command",
                    "args": {
                        "CommandLine": cmd,
                    },
                }
            }
            res = self.run_hook(payload)
            self.assertEqual(
                res.get("decision"),
                "deny",
                f"Failed to block dangerous shell command: '{cmd}'",
            )

    def test_06_normal_read_operation(self):
        """5. Normal read operation (cat, grep, python script query) -> ALLOW."""
        safe_commands = [
            "cat campus-helpdesk-plugin/skills/timetable-helper/data/timetable.csv",
            "head -n 5 data/timetable.csv",
            "grep 'Data Structures' data/timetable.csv",
            "python3 scripts/timetable_lookup.py --day Monday",
        ]
        for cmd in safe_commands:
            payload = {
                "toolCall": {
                    "name": "run_command",
                    "args": {
                        "CommandLine": cmd,
                    },
                }
            }
            res = self.run_hook(payload)
            self.assertEqual(
                res.get("decision"),
                "allow",
                f"Incorrectly blocked safe read command: '{cmd}'",
            )

    def test_07_unrelated_file_modification(self):
        """6. Unrelated file modification (write_file to notes.txt) -> ALLOW."""
        payload = {
            "toolCall": {
                "name": "write_file",
                "args": {
                    "Path": "/Users/student/project/notes.txt",
                    "Content": "Meeting notes for coursework",
                },
            }
        }
        res = self.run_hook(payload)
        self.assertEqual(res.get("decision"), "allow")

    def test_08_malformed_and_empty_input_handling(self):
        """7. Malformed and empty input: must fail safe and DENY, never silently allow."""
        # Malformed JSON
        malformed_json = '{"toolCall": { invalid json syntax '
        res_malformed = self.run_hook(malformed_json)
        self.assertEqual(res_malformed.get("decision"), "deny")
        self.assertIn("malformed", res_malformed.get("reason", "").lower())

        # Empty string input
        res_empty = self.run_hook("")
        self.assertEqual(res_empty.get("decision"), "deny")


if __name__ == "__main__":
    unittest.main(verbosity=2)
