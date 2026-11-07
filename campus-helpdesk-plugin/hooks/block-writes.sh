#!/usr/bin/env bash
# block-writes.sh
# PreToolUse hook script that blocks write/edit operations to data/timetable.csv

python3 -c '
import sys
import json

try:
    input_data = sys.stdin.read().strip()
    if not input_data:
        # Default allow if no input piped
        print(json.dumps({"decision": "allow"}))
        sys.exit(0)

    payload = json.loads(input_data)
    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    path_arg = str(args.get("Path", ""))
    cmd_arg = str(args.get("CommandLine", ""))

    blocked = False
    reason = "Write operations to data/timetable.csv are blocked to protect dataset integrity."

    # Block write_file and edit_file targeting timetable.csv
    if "timetable.csv" in path_arg and tool_name in ["write_file", "edit_file"]:
        blocked = True

    # Block shell commands that overwrite, remove, or alter timetable.csv
    if "timetable.csv" in cmd_arg:
        dangerous_ops = [">", "rm ", "truncate", "mv ", "sed ", "awk -i", "cp "]
        if any(op in cmd_arg for op in dangerous_ops):
            blocked = True

    if blocked:
        print(json.dumps({
            "decision": "deny",
            "reason": reason
        }))
    else:
        print(json.dumps({"decision": "allow"}))
except Exception as e:
    print(json.dumps({"decision": "allow", "error": str(e)}))
'

