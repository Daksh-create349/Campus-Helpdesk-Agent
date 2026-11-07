---
name: check-schedule
description: Look up and check student class schedules, timings, faculty, and room locations using the timetable-helper skill.
---

# /check-schedule

Instructs the agent to look up class schedules using the `timetable-helper` skill.

## Trigger Instructions

When the user invokes `/check-schedule` (e.g., `/check-schedule Monday`, `/check-schedule "Data Structures"`):

1. **Activate Skill**: Use the `timetable-helper` skill located at `skills/timetable-helper/`.
2. **Execute Lookup**:
   Run the CLI helper script to fetch schedule records:
   ```bash
   python3 campus-helpdesk-plugin/skills/timetable-helper/scripts/timetable_lookup.py [options]
   ```
3. **Parse Arguments**:
   - If a weekday is specified (e.g., `Monday`), filter with `--day <day>`.
   - If a course or subject is specified (e.g., `Data Structures`), filter with `--subject "<subject>"`.
   - If semester or section is provided, filter with `--semester <num>` and `--section <sec>`.
   - If no arguments are provided, query and display the weekly overview for Semester 3, Section A.
4. **Response Protocol**:
   - Only report records present in `data/timetable.csv`.
   - If no classes match, state clearly that no scheduled records were found.
   - Present results with **Day**, **Time**, **Subject**, **Faculty**, and **Room**.

