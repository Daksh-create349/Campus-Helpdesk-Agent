# Campus Helpdesk MCP Server

A lightweight Model Context Protocol (MCP) server built with Python and the official `mcp` SDK, operating over standard input/output (`stdio`).

This server provides tools and resources for student timetable lookup, fee status verification, and hostel policy guidelines.

---

## Capabilities

### 1. Tools

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_timetable` | `batch` (string), `day` (string) | Returns mock class timetable records for Semester 3, Section A. |
| `get_fee_status` | `student_id` (string) | Returns payment status (`Paid`, `Pending`, `Overdue`) and balance details for a student. |

### 2. Resources

| Resource Name | URI | Description |
| :--- | :--- | :--- |
| `hostel_rules` | `hostel://rules` | Markdown document detailing hostel gate timings, curfew, quiet hours, and safety rules. |

---

## Prerequisites

- **Python**: Version 3.10 or higher.
- **Official MCP SDK**: `mcp`

---

## Installation

Install the official Python MCP SDK using `pip` (no other third-party dependencies required):

```bash
pip install mcp
```

*(If using Anaconda or Python 3 explicitly)*:
```bash
python3 -m pip install mcp
```

---

## Running the Server

### 1. Direct Execution over `stdio`

Run the server directly from the `mcp-server` directory:

```bash
cd mcp-server
python3 server.py
```

Because this is a `stdio` server, it communicates over standard input/output via JSON-RPC. It is designed to be spawned by an MCP host/client.

### 2. Interactive Testing via MCP Inspector

You can inspect and test all tools and resources interactively in a web UI using the official MCP Inspector:

```bash
npx @modelcontextprotocol/inspector python3 mcp-server/server.py
```

This will launch a local browser interface where you can call `get_timetable`, test `get_fee_status`, and view the `hostel://rules` resource.

---

## Client Integration

### Antigravity Configuration (`mcp_config.json`)

To connect this MCP server to Antigravity, add the following entry to your `~/.gemini/config/mcp_config.json` (or workspace MCP settings):

```json
{
  "mcpServers": {
    "campus-helpdesk": {
      "command": "python3",
      "args": [
        "/Users/dakshsrivastava/Desktop/Campus-Helpdesk-Agent/mcp-server/server.py"
      ]
    }
  }
}
```

### Claude Desktop Configuration (`claude_desktop_config.json`)

On macOS (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "campus-helpdesk": {
      "command": "python3",
      "args": [
        "/Users/dakshsrivastava/Desktop/Campus-Helpdesk-Agent/mcp-server/server.py"
      ]
    }
  }
}
```

---

## Mock Test Data

### Sample Student IDs for `get_fee_status`
- `STU1001` — **Paid** (Aarav Sharma, $0.00 due)
- `STU1002` — **Pending** (Ananya Patel, $1,250.00 due by 2026-11-20)
- `STU1003` — **Overdue** (Rohan Iyer, $2,500.00 past due)
- `STU1004` — **Paid** (Sneha Kulkarni, $0.00 due)
- `STU1005` — **Pending** (Vikram Singh, $600.00 lab fee due)

### Sample Query for `get_timetable`
- `batch`: `"Semester 3, Section A"` (or `"3A"`)
- `day`: `"Monday"` *(Returns Data Structures, DBMS, and Operating Systems)*

