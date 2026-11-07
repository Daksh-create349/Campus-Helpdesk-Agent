#!/usr/bin/env bash
# block-writes.sh
# PreToolUse hook script that blocks unauthorized write/edit operations to timetable.csv
# Compatible with Google Antigravity and Agent Tooling specifications.

python3 -c '
import sys
import json
import re

def process_hook():
    try:
        input_data = sys.stdin.read().strip()
    except Exception as read_err:
        print(json.dumps({"decision": "deny", "reason": f"Failed reading stdin: {read_err}"}))
        sys.exit(0)

    if not input_data:
        # Fail-safe: empty input is blocked to avoid bypasses
        print(json.dumps({"decision": "deny", "reason": "Empty hook payload received - blocked for security"}))
        sys.exit(0)

    try:
        payload = json.loads(input_data)
    except Exception as parse_err:
        # Critical rule: Do NOT silently allow operations when the hook fails to parse input
        print(json.dumps({
            "decision": "deny",
            "reason": f"Malformed JSON payload in PreToolUse hook: {parse_err}. Blocked for data integrity."
        }))
        sys.exit(0)

    tool_call = payload.get("toolCall", {})
    tool_name = str(tool_call.get("name", "")).strip().lower()
    args = tool_call.get("args", {})

    # Extract all possible file path arguments across various agent specifications
    target_paths = []
    for key in ["Path", "path", "TargetFile", "target_file", "file_path", "filePath", "Target", "target"]:
        val = args.get(key)
        if val:
            target_paths.append(str(val))

    # Also inspect any nested files list or replacements
    files_arg = args.get("files") or args.get("Files")
    if isinstance(files_arg, list):
        for item in files_arg:
            if isinstance(item, str):
                target_paths.append(item)
            elif isinstance(item, dict):
                for subkey in ["Path", "path", "TargetFile", "target_file", "file_path"]:
                    if item.get(subkey):
                        target_paths.append(str(item.get(subkey)))

    # Direct file modification tools
    file_write_tools = [
        "write_file",
        "edit_file",
        "write_to_file",
        "replace_file_content",
        "multi_replace_file_content",
    ]

    # Check direct tool operations targeting timetable.csv
    targets_timetable = any("timetable.csv" in p for p in target_paths)

    if targets_timetable and any(t in tool_name for t in file_write_tools):
        print(json.dumps({
            "decision": "deny",
            "reason": "Direct modification to protected dataset timetable.csv is strictly denied to preserve data integrity."
        }))
        sys.exit(0)

    # Shell command execution tools
    if "run_command" in tool_name or "command" in tool_name or "execute" in tool_name:
        cmd_arg = str(args.get("CommandLine") or args.get("command") or args.get("cmd") or "")
        
        if "timetable.csv" in cmd_arg:
            # Dangerous shell patterns that alter, remove, truncate or redirect to timetable.csv
            dangerous_patterns = [
                r">\s*[^|;&]*timetable\.csv",       # Redirect overwrite: > timetable.csv
                r">>\s*[^|;&]*timetable\.csv",      # Redirect append: >> timetable.csv
                r"\brm\b",                           # Remove file
                r"\bunlink\b",                       # Unlink file
                r"\btruncate\b",                     # Truncate
                r"\bmv\b",                           # Move / Rename
                r"\bcp\b\s+.*timetable\.csv",        # Copy over timetable.csv
                r"\bsed\s+-[a-zA-Z]*i\b",            # In-place sed
                r"\bawk\s+-i\b",                     # In-place awk
                r"\btee\b",                          # Tee writing
                r"\btouch\b",                        # Touch timestamp
                r"\b(nano|vim|vi|emacs)\b",          # Interactive editor
                r"\bopen\s*\([^)]*[\x27\x22][wa\+]", # Python file write mode: open(..., "w")
            ]

            is_destructive = any(re.search(pat, cmd_arg) for pat in dangerous_patterns)

            if is_destructive:
                print(json.dumps({
                    "decision": "deny",
                    "reason": f"Shell command attempting modification to protected dataset timetable.csv is denied: {cmd_arg}"
                }))
                sys.exit(0)

    # Allow all legitimate read operations and unrelated modifications
    print(json.dumps({"decision": "allow"}))

if __name__ == "__main__":
    process_hook()
'
