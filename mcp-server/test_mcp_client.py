#!/usr/bin/env python3
"""
test_mcp_client.py
A standalone Python MCP client that spawns 'server.py' over stdio using subprocess.
Demonstrates the full raw JSON-RPC 2.0 message exchange for:
1. 'initialize'
2. 'tools/list'
3. 'tools/call' for 'get_timetable'
4. 'tools/call' for 'get_fee_status' (failure case with INVALID999)
"""

import json
from pathlib import Path
import shutil
import subprocess
import sys


def find_mcp_python() -> str:
    """Find a Python interpreter that has the official 'mcp' SDK installed."""
    candidates = [
        "/opt/anaconda3/bin/python3",
        "/opt/anaconda3/bin/python",
        str(Path.home() / ".gemini" / "antigravity" / "bin" / "python3"),
        str(Path.home() / ".local" / "bin" / "python3"),
        sys.executable,
        shutil.which("python3.13") or "",
        shutil.which("python3.12") or "",
        shutil.which("python3.11") or "",
        shutil.which("python3.10") or "",
    ]

    for cand in candidates:
        if cand and Path(cand).exists():
            try:
                res = subprocess.run(
                    [cand, "-c", "import mcp"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if res.returncode == 0:
                    return cand
            except Exception:
                continue

    return sys.executable


def print_step(step_num: int, title: str):
    divider = "=" * 80
    print(f"\n{divider}")
    print(f"STEP {step_num}: {title}")
    print(f"{divider}")


def print_exchange(label: str, data: dict):
    print(f"\n[{label}]")
    print(json.dumps(data, indent=2))


def main():
    script_dir = Path(__file__).resolve().parent
    server_script = script_dir / "server.py"

    if not server_script.exists():
        print(f"Error: Server script not found at {server_script}", file=sys.stderr)
        sys.exit(1)

    # Detect python interpreter with mcp installed
    python_bin = find_mcp_python()

    print("================================================================================")
    print("STARTING MCP STDIO TEST CLIENT")
    print(f"Server Target: {server_script}")
    print(f"Python Interpreter: {python_bin}")
    print("================================================================================")

    # Spawn the MCP server as a subprocess communicating over stdio
    process = subprocess.Popen(
        [python_bin, str(server_script)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    def send_request(req_obj: dict) -> dict:
        """Send a JSON-RPC request and return parsed response."""
        print_exchange("CLIENT REQUEST (RAW JSON-RPC)", req_obj)
        raw_payload = json.dumps(req_obj) + "\n"
        process.stdin.write(raw_payload)
        process.stdin.flush()

        # Read the single line JSON response from stdout
        raw_response = process.stdout.readline()
        if not raw_response:
            stderr_out = process.stderr.read()
            raise RuntimeError(
                f"Server closed connection unexpectedly.\n"
                f"Stderr: {stderr_out}\n"
                f"Interpreter used: {python_bin}"
            )

        res_obj = json.loads(raw_response.strip())
        print_exchange("SERVER RESPONSE (RAW JSON-RPC)", res_obj)
        return res_obj

    def send_notification(notify_obj: dict):
        """Send a one-way notification without expecting a response."""
        print_exchange("CLIENT NOTIFICATION (RAW JSON-RPC)", notify_obj)
        raw_payload = json.dumps(notify_obj) + "\n"
        process.stdin.write(raw_payload)
        process.stdin.flush()

    try:
        # ----------------------------------------------------------------------
        # Step 1: Initialize Request
        # ----------------------------------------------------------------------
        print_step(1, "Initialize Request and Handshake")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": False},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-mcp-client",
                    "version": "1.0.0"
                }
            }
        }
        send_request(init_request)

        # Send standard initialized notification
        send_notification({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        })

        # ----------------------------------------------------------------------
        # Step 2: Tools List Request
        # ----------------------------------------------------------------------
        print_step(2, "tools/list Request (Discover Available Tools)")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        send_request(list_tools_request)

        # ----------------------------------------------------------------------
        # Step 3: Tools Call Request for get_timetable
        # ----------------------------------------------------------------------
        print_step(3, "tools/call: 'get_timetable' (Semester 3, Section A - Monday)")
        call_timetable_request = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "get_timetable",
                "arguments": {
                    "batch": "Semester 3, Section A",
                    "day": "Monday"
                }
            }
        }
        send_request(call_timetable_request)

        # ----------------------------------------------------------------------
        # Step 4: Tools Call Request for get_fee_status (Failure Case: INVALID999)
        # ----------------------------------------------------------------------
        print_step(4, "tools/call: 'get_fee_status' (Failure Case: INVALID999)")
        call_fee_request = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "get_fee_status",
                "arguments": {
                    "student_id": "INVALID999"
                }
            }
        }
        send_request(call_fee_request)

        print("\n================================================================================")
        print("ALL 4 MCP JSON-RPC TEST STEPS COMPLETED SUCCESSFULLY!")
        print("================================================================================")

    except Exception as exc:
        print(f"\nTest execution encountered an error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        # Cleanly terminate child process
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=3)


if __name__ == "__main__":
    main()
