# USCIS Case Status Tracker

A local Gradio dashboard for tracking USCIS case status. It stores a history of every snapshot you fetch and highlights exactly what changed between checks.

## Features


- **Case status overview** — Form type, applicant, representative, submission date, last updated, action required flag, and processing completion status.
- **Change detection** — Compares each new snapshot against the previous one and shows added, removed, and changed fields with color coding.
- **Event timeline** — Chronological view of all case events, notices, and appointments, sorted newest-first.
- **Snapshot history** — Table of every snapshot saved for a case with timestamps.
- **Multi-case support** — Searchable dropdown populated from existing histories. Type a new ID to start tracking a new case.
- **Persistent storage** — Each case ID's history is saved as a JSON list in `case_history/<ID>.json` and is persistent across restarts. Delete `case_history` to clear all local data.
- **Dark mode** — UI adapts to Gradio's dark mode toggle and the OS-level `prefers-color-scheme` preference.

## Setup

```bash
pip install gradio
python app.py
```

Then open the URL printed in the terminal (default: http://localhost:7860).

## How to use

The USCIS case API requires you to be logged in. Because the dashboard runs locally and cannot share your browser session, the workflow is:

1. **Log in** to [my.uscis.gov](https://my.uscis.gov) in your browser.
2. **Select or enter a Case ID** in the dropdown (e.g. `ABC1234567890`).
   - Existing cases appear as dropdown options populated from `case_history/`.
   - Type a new ID to start tracking a case for the first time.
3. **Click the link** that appears below the dropdown. It opens the case API endpoint directly in your browser tab.
   - If you get an error page, you may have been logged out — log in again, then click the link once more.
4. Your browser displays raw JSON. **Select all and copy** (`⌘ + A` then `⌘ + C` on Mac, `Ctrl + A` / `Ctrl + C` on Windows).
5. **Paste** the JSON into the text box in the dashboard.
6. Click **Process** (or press Enter in the JSON box).

The dashboard saves the snapshot and displays the results across five tabs:

| Tab | Contents |
|-----|----------|
| 📋 Status | Key case fields at a glance |
| 🔄 Changes | Diff against the previous snapshot |
| 📅 Timeline | Events and notices in reverse-chronological order |
| 🗂 History | List of all saved snapshots for this case |
| { } Raw JSON | Full API response |

Repeat steps 3–6 whenever you want to check for updates. The Changes tab will highlight anything that moved since your last check.

## File layout

```
.
├── app.py              # Application logic and Gradio UI
├── styles.css          # All custom CSS (light + dark mode)
├── requirements.txt    # Python dependencies
└── case_history/
    └── <CASE_ID>.json  # One file per case; each fetch appended as a list entry
```

### History file format

```json
[
  {
    "fetchedAt": "2026-05-04T10:23:00.000000",
    "response": { "data": { ... } }
  },
  {
    "fetchedAt": "2026-05-10T08:45:12.000000",
    "response": { "data": { ... } }
  }
]
```

The dashboard always compares the newest fetch against the last entry in this list.
