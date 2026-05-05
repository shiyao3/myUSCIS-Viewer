import json
from datetime import datetime
from pathlib import Path

import gradio as gr

CUSTOM_CSS = Path("styles.css").read_text()
HISTORY_DIR = Path("case_history")
HISTORY_DIR.mkdir(exist_ok=True)

API_BASE = "https://my.uscis.gov/account/case-service/api/cases/"


# History

def _history_path(case_id: str) -> Path:
    return HISTORY_DIR / f"{case_id.strip()}.json"


def load_history(case_id: str) -> list:
    path = _history_path(case_id)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return []
    return []


def append_history(case_id: str, response: dict):
    history = load_history(case_id)
    history.append({"fetchedAt": datetime.now().isoformat(), "response": response})
    _history_path(case_id).write_text(json.dumps(history, indent=2))


def list_case_ids() -> list[str]:
    return sorted(p.stem for p in HISTORY_DIR.glob("*.json"))


# Diff

def flatten_diff(old: dict, new: dict, path: str = "") -> list:
    changes = []
    for k in sorted(set(old) | set(new)):
        p = f"{path}.{k}" if path else k
        if k not in old:
            changes.append(("added", p, None, new[k]))
        elif k not in new:
            changes.append(("removed", p, old[k], None))
        elif isinstance(old[k], dict) and isinstance(new[k], dict):
            changes.extend(flatten_diff(old[k], new[k], p))
        elif old[k] != new[k]:
            changes.append(("changed", p, old[k], new[k]))
    return changes


def _fmt(v) -> str:
    s = json.dumps(v) if isinstance(v, (dict, list)) else str(v)
    return (s[:180] + "…") if len(s) > 180 else s


# Renderers

def render_status(data: dict, case_id: str, fetch_count: int) -> str:
    action_cls  = "uc-warn" if data.get("actionRequired") else "uc-ok"
    action_text = "YES — Action Required!" if data.get("actionRequired") else "No"
    closed_text  = "Yes" if data.get("closed") else "In progress"
    complete_text = "Yes" if data.get("areAllGroupStatusesComplete") else "No"

    rows = [
        ("Case ID",             f'<span style="font-family:monospace;">{case_id}</span>'),
        ("Receipt Number",      f'<span style="font-family:monospace;">{data.get("receiptNumber","N/A")}</span>'),
        ("Form",                f'{data.get("formType","?")} — {data.get("formName","Unknown")}'),
        ("Applicant",           data.get("applicantName", "N/A")),
        ("Representative",      data.get("representativeName", "N/A")),
        ("Submission Date",     data.get("submissionDate", "N/A")),
        ("Last Updated",        f'<strong>{data.get("updatedAt","N/A")}</strong>'),
        ("Status",              closed_text),
        ("Action Required",     f'<strong class="{action_cls}">{action_text}</strong>'),
        ("Processing Complete", complete_text),
    ]

    rows_html = "".join(
        f'<tr><td class="uc-lbl">{label}</td><td class="uc-val">{val}</td></tr>'
        for label, val in rows
    )

    return (
        f'<div class="uc-card">'
        f'<h3>Case Overview</h3>'
        f'<table class="uc-tbl">{rows_html}</table>'
        f'<p class="uc-muted" style="margin:12px 0 0;font-size:0.8em;">'
        f'Processed {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} · {fetch_count} snapshot(s) stored</p>'
        f'</div>'
    )


def render_changes(changes: list) -> str:
    if not changes:
        return "<p class='uc-ok'>✓ No changes detected since last snapshot.</p>"

    cls_map   = {"added": "uc-add",  "removed": "uc-rem",     "changed": "uc-chg"}
    label_map = {"added": "+ ADDED", "removed": "− REMOVED",  "changed": "~ CHANGED"}
    html = f"<p><strong>{len(changes)} change(s) detected:</strong></p>"
    for ctype, path, old, new in changes:
        if ctype == "added":
            detail = f"= <code>{_fmt(new)}</code>"
        elif ctype == "removed":
            detail = f"was: <code>{_fmt(old)}</code>"
        else:
            detail = f"<code>{_fmt(old)}</code> → <code>{_fmt(new)}</code>"
        html += (
            f'<div class="{cls_map[ctype]}">'
            f'<span class="dl">{label_map[ctype]}</span> '
            f'<code>{path}</code><br>&nbsp;&nbsp;{detail}</div>'
        )
    return html


def render_timeline(data: dict) -> str:
    items = []

    sub_date = data.get("submissionDate", "")
    if sub_date:
        items.append({
            "ts":    data.get("submissionTimestamp", sub_date),
            "date":  sub_date,
            "label": "Case Submitted",
            "lcls":  "uc-cgreen",
            "detail": f'{data.get("formType","")} filed via {data.get("elisChannelType","")}',
            "icon":  "📄",
        })

    for n in data.get("notices", []):
        appt = n.get("appointmentDateTime", "")
        items.append({
            "ts":    n.get("generationDate", ""),
            "date":  n.get("generationDate", "")[:10],
            "label": n.get("actionType", "Notice"),
            "lcls":  "uc-cpurple",
            "detail": f'Appointment: {appt[:16].replace("T"," ")}' if appt else "",
            "icon":  "📬",
        })

    for e in data.get("events", []):
        items.append({
            "ts":    e.get("eventTimestamp", e.get("eventDateTime", "")),
            "date":  e.get("eventDateTime", ""),
            "label": e.get("eventCode", "Event"),
            "lcls":  "uc-cblue",
            "detail": f'ID: {e.get("eventId","")[:8]}…',
            "icon":  "●",
        })

    items.sort(key=lambda x: x["ts"], reverse=True)

    if not items:
        return "<p class='uc-muted'>No events or notices found.</p>"

    html = '<div class="uc-tline">'
    for item in items:
        html += (
            f'<div style="position:relative;margin-bottom:16px;">'
            f'<div style="position:absolute;left:-20px;top:8px;font-size:1.1em;">{item["icon"]}</div>'
            f'<div class="uc-tbody">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;">'
            f'<strong class="{item["lcls"]}">{item["label"]}</strong>'
            f'<span class="uc-tdate">{item["date"]}</span></div>'
            + (f'<div class="uc-tdetail">{item["detail"]}</div>' if item["detail"] else "")
            + '</div></div>'
        )
    html += "</div>"
    return html


def render_history_list(case_id: str) -> str:
    if not case_id.strip():
        return ""
    history = load_history(case_id)
    if not history:
        return "<p class='uc-muted' style='font-size:0.9em;'>No snapshots yet for this case.</p>"

    rows = "".join(
        f'<tr class="uc-hrow">'
        f'<td class="uc-hidx">#{i+1}</td>'
        f'<td style="font-family:monospace;">{entry["fetchedAt"][:19].replace("T"," ")}</td>'
        f'<td>{entry["response"].get("data",{}).get("updatedAt","—")}</td>'
        f'</tr>'
        for i, entry in enumerate(history)
    )
    return (
        f'<table class="uc-tbl">'
        f'<tr class="uc-hhdr"><th>Snapshot</th><th>Saved at</th><th>Case updated at</th></tr>'
        f'{rows}</table>'
    )


# URL Helper

def update_url(case_id: str) -> str:
    cid = case_id.strip()
    if not cid:
        return ""
    url = API_BASE + cid
    return (
        f"**Step 2 — open this URL while logged in to my.uscis.gov** "
        f"(if you see an error, log in first then click again):\n\n"
        f"[{url}]({url})"
    )


# Main Handler

def process_json(case_id: str, raw_json: str):
    no_dd = gr.update()  # leave dropdown unchanged on early exit
    case_id = case_id.strip()

    if not case_id:
        return ("<p class='uc-warn'>Enter a Case ID first.</p>", "", "", "", "", no_dd)
    if not raw_json.strip():
        return ("<p class='uc-warn'>Paste the JSON from the URL above.</p>", "", "", "", "", no_dd)

    try:
        response = json.loads(raw_json)
    except json.JSONDecodeError as e:
        return (f"<p class='uc-warn'>Invalid JSON: {e}</p>", "", "", "", "", no_dd)

    data = response.get("data", {})
    if not data:
        return ("<p class='uc-warn'>Unexpected JSON — no \"data\" key found.</p>", "", "", "", "", no_dd)

    history = load_history(case_id)

    if history:
        last_data = history[-1].get("response", {}).get("data", {})
        changes_html = render_changes(flatten_diff(last_data, data))
    else:
        changes_html = "<p class='uc-muted'>First snapshot — nothing to compare yet.</p>"

    append_history(case_id, response)

    return (
        render_status(data, case_id, len(history) + 1),
        changes_html,
        render_timeline(data),
        render_history_list(case_id),
        json.dumps(response, indent=2),
        gr.update(choices=list_case_ids(), value=case_id),
    )


# UI Components

INSTRUCTIONS = """
## Usage

1. Log in to [my.uscis.gov](https://my.uscis.gov) first. *If you see an error page, log in, then click the link again.*
2. **Enter your Case ID** below (e.g. `ABC1234567890`).
3. **Click the link** that appears — it opens the case API in your browser.
4. Your browser shows raw JSON. **Select all → Copy** (`Cmd+A`, `Cmd+C`).
5. **Paste** into the box below and click **Process**.

Each case ID's history is stored separately in `case_history/`. Paste again anytime to see what changed.
"""

with gr.Blocks(title="USCIS Case Tracker", theme=gr.themes.Soft(), css=CUSTOM_CSS) as app:
    gr.Markdown("# USCIS Case Status Tracker")
    gr.Markdown(INSTRUCTIONS)

    with gr.Row():
        case_id_input = gr.Dropdown(
            label="Case ID",
            choices=list_case_ids(),
            allow_custom_value=True,
            filterable=True,
            scale=1,
            info="Select an existing case or type a new one (e.g. ABC1234567890)",
        )

    url_display = gr.Markdown(value="")

    json_input = gr.Textbox(
        label="Paste JSON here",
        placeholder='{"data": {"receiptNumber": "ABC...", ...}}',
        lines=6,
        max_lines=12,
    )

    process_btn = gr.Button("Process", variant="primary", scale=0, min_width=110)

    with gr.Tabs():
        with gr.Tab("📋 Status"):
            status_out = gr.HTML()
        with gr.Tab("🔄 Changes"):
            changes_out = gr.HTML()
        with gr.Tab("📅 Timeline"):
            timeline_out = gr.HTML()
        with gr.Tab("🗂 History"):
            history_out = gr.HTML()
        with gr.Tab("{ } Raw JSON"):
            raw_out = gr.Code(language="json", show_label=False)

    case_id_input.change(update_url, inputs=case_id_input, outputs=url_display)

    proc_outputs = [status_out, changes_out, timeline_out, history_out, raw_out, case_id_input]
    process_btn.click(process_json, inputs=[case_id_input, json_input], outputs=proc_outputs)
    json_input.submit(process_json, inputs=[case_id_input, json_input], outputs=proc_outputs)


if __name__ == "__main__":
    app.launch()
