#!/usr/bin/env python3
"""
test_mcp_client.py
Comprehensive standalone Python MCP client that spawns 'server.py' over stdio using subprocess.
Demonstrates the complete raw JSON-RPC 2.0 message exchange across all 9 verification operations:
1. 'initialize' protocol handshake
2. 'tools/list' discovery
3. Successful 'tools/call' for 'get_timetable' (Semester 3, Section A - Monday)
4. Successful 'tools/call' for 'get_fee_status' (STU1001)
5. 'tools/call' for 'get_fee_status' with an invalid ID (INVALID999)
6. 'tools/call' for 'get_timetable' with unsupported semester (Semester 5, Section A)
7. 'tools/call' for 'get_timetable' with Section B (Semester 3, Section B) - verifying Section A records are not returned
8. 'tools/call' for 'get_timetable' with invalid day ('Funday')
9. 'resources/read' for hostel rules ('hostel://rules')
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
    print("STARTING MCP STDIO TEST CLIENT (9-STEP VERIFICATION SUITE)")
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

    req_id_counter = 1

    def send_request(method: str, params: dict) -> dict:
        """Send a JSON-RPC request and return parsed response."""
        nonlocal req_id_counter
        req_obj = {
            "jsonrpc": "2.0",
            "id": req_id_counter,
            "method": method,
            "params": params,
        }
        req_id_counter += 1

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

    def send_notification(method: str, params: dict = None):
        """Send a one-way notification without expecting a response."""
        notify_obj = {
            "jsonrpc": "2.0",
            "method": method,
        }
        if params is not None:
            notify_obj["params"] = params

        print_exchange("CLIENT NOTIFICATION (RAW JSON-RPC)", notify_obj)
        raw_payload = json.dumps(notify_obj) + "\n"
        process.stdin.write(raw_payload)
        process.stdin.flush()

    try:
        # ----------------------------------------------------------------------
        # Step 1: Initialize Request
        # ----------------------------------------------------------------------
        print_step(1, "Initialize Request and Capability Negotiation Handshake")
        init_res = send_request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": False},
                    "sampling": {},
                },
                "clientInfo": {
                    "name": "campus-helpdesk-test-client",
                    "version": "1.0.0",
                },
            },
        )
        assert "result" in init_res, "Initialize handshake failed!"

        # Send standard initialized notification
        send_notification("notifications/initialized")

        # ----------------------------------------------------------------------
        # Step 2: Tools List Request
        # ----------------------------------------------------------------------
        print_step(2, "tools/list Request (Discover Available Tools)")
        tools_res = send_request("tools/list", {})
        assert "result" in tools_res and "tools" in tools_res["result"]
        tool_names = [t["name"] for t in tools_res["result"]["tools"]]
        print(f"\nDiscovered Tools: {tool_names}")
        assert "get_timetable" in tool_names and "get_fee_status" in tool_names

        # ----------------------------------------------------------------------
        # Step 3: Successful tools/call for get_timetable
        # ----------------------------------------------------------------------
        print_step(3, "tools/call: 'get_timetable' (Semester 3, Section A - Monday)")
        call_tt = send_request(
            "tools/call",
            {
                "name": "get_timetable",
                "arguments": {
                    "batch": "Semester 3, Section A",
                    "day": "Monday",
                },
            },
        )
        tt_text = call_tt["result"]["content"][0]["text"]
        tt_data = json.loads(tt_text)
        assert tt_data["status"] == "success"
        assert tt_data["count"] == 3
        print(f"\nVerified: Successfully retrieved {tt_data['count']} classes for Monday!")

        # ----------------------------------------------------------------------
        # Step 4: Successful tools/call for get_fee_status
        # ----------------------------------------------------------------------
        print_step(4, "tools/call: 'get_fee_status' (Valid Student: STU1001)")
        call_fee_valid = send_request(
            "tools/call",
            {
                "name": "get_fee_status",
                "arguments": {
                    "student_id": "STU1001",
                },
            },
        )
        fee_valid_text = call_fee_valid["result"]["content"][0]["text"]
        fee_valid_data = json.loads(fee_valid_text)
        assert fee_valid_data["status"] == "success"
        assert fee_valid_data["record"]["status"] == "Paid"
        print(f"\nVerified: Fee record found for STU1001 with status '{fee_valid_data['record']['status']}'!")

        # ----------------------------------------------------------------------
        # Step 5: tools/call for get_fee_status (Invalid ID: INVALID999)
        # ----------------------------------------------------------------------
        print_step(5, "tools/call: 'get_fee_status' (Invalid ID: INVALID999 - Application Error)")
        call_fee_invalid = send_request(
            "tools/call",
            {
                "name": "get_fee_status",
                "arguments": {
                    "student_id": "INVALID999",
                },
            },
        )
        fee_invalid_text = call_fee_invalid["result"]["content"][0]["text"]
        fee_invalid_data = json.loads(fee_invalid_text)
        assert fee_invalid_data["status"] == "not_found"
        print("\nVerified: Graceful application-level error returned with sample IDs.")

        # ----------------------------------------------------------------------
        # Step 6: tools/call for get_timetable with unsupported semester
        # ----------------------------------------------------------------------
        print_step(6, "tools/call: 'get_timetable' (Unsupported Semester: Semester 5, Section A)")
        call_tt_unsupp = send_request(
            "tools/call",
            {
                "name": "get_timetable",
                "arguments": {
                    "batch": "Semester 5, Section A",
                    "day": "Monday",
                },
            },
        )
        tt_unsupp_data = json.loads(call_tt_unsupp["result"]["content"][0]["text"])
        assert tt_unsupp_data["status"] == "not_found"
        assert "semester '5'" in tt_unsupp_data["message"].lower()
        print("\nVerified: Unsupported semester correctly rejected with descriptive error.")

        # ----------------------------------------------------------------------
        # Step 7: tools/call for get_timetable with Section B
        # ----------------------------------------------------------------------
        print_step(7, "tools/call: 'get_timetable' (Section B Verification: Never return Section A)")
        call_tt_sec_b = send_request(
            "tools/call",
            {
                "name": "get_timetable",
                "arguments": {
                    "batch": "Semester 3, Section B",
                    "day": "Monday",
                },
            },
        )
        tt_sec_b_data = json.loads(call_tt_sec_b["result"]["content"][0]["text"])
        assert tt_sec_b_data["status"] == "not_found"
        assert len(tt_sec_b_data["records"]) == 0
        assert "section 'b'" in tt_sec_b_data["message"].lower()
        print("\nVerified: Section B query safely returns not_found without leaking Section A records!")

        # ----------------------------------------------------------------------
        # Step 8: tools/call for get_timetable with invalid day
        # ----------------------------------------------------------------------
        print_step(8, "tools/call: 'get_timetable' (Invalid Day: 'Funday')")
        call_tt_bad_day = send_request(
            "tools/call",
            {
                "name": "get_timetable",
                "arguments": {
                    "batch": "Semester 3, Section A",
                    "day": "Funday",
                },
            },
        )
        tt_bad_day_data = json.loads(call_tt_bad_day["result"]["content"][0]["text"])
        assert tt_bad_day_data["status"] == "error"
        assert "invalid day" in tt_bad_day_data["message"].lower()
        print("\nVerified: Invalid day rejected with error response.")

        # ----------------------------------------------------------------------
        # Step 9: resources/read for hostel rules
        # ----------------------------------------------------------------------
        print_step(9, "resources/read: Retrieve 'hostel://rules' Markdown Document")
        res_read = send_request(
            "resources/read",
            {
                "uri": "hostel://rules",
            },
        )
        assert "result" in res_read and "contents" in res_read["result"]
        doc_content = res_read["result"]["contents"][0]["text"]
        assert "Hostel Rules and Regulations" in doc_content
        print(f"\nVerified: Successfully retrieved hostel rules resource ({len(doc_content)} characters)!")

        print("\n" + "=" * 80)
        print("ALL 9 MCP JSON-RPC TEST STEPS COMPLETED AND VERIFIED SUCCESSFULLY!")
        print("=" * 80)

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
