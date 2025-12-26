import json
import re
from pathlib import Path
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT
from reportlab.lib import colors


ILLEGAL = re.compile(r"[\x00-\x08\x0B-\x0C\x0E-\x1F]")


def clean(v):
    return ILLEGAL.sub("", str(v)) if v else ""


def extract_json_blocks(md_text):
    blocks = []
    for sec in md_text.split("<details>")[1:]:
        if "```json" not in sec:
            continue
        try:
            txt = sec.split("```json", 1)[1].split("```", 1)[0]
            blocks.append(json.loads(txt.strip()))
        except Exception:
            continue
    return blocks


def normalize_issue(obj):
    issue = {}
    for k, v in obj.items():
        lk = k.lower()
        if "file" in lk or "path" in lk:
            issue["File"] = v
        if "rule" in lk or "id" in lk:
            issue["Rule"] = v
        if "severity" in lk or "level" in lk:
            issue["Severity"] = v
        if "message" in lk or "title" in lk or "description" in lk:
            issue["Message"] = v
    return issue


def find_issues(data):
    issues = []

    if isinstance(data, dict):
        found = normalize_issue(data)
        if len(found) >= 2:
            issues.append(found)
        for v in data.values():
            issues.extend(find_issues(v))

    elif isinstance(data, list):
        for i in data:
            issues.extend(find_issues(i))

    return issues


def build_report(md_path, docx_out, pdf_out):
    md = Path(md_path).read_text(encoding="utf-8", errors="ignore")
    blocks = extract_json_blocks(md)

    all_issues = []
    for b in blocks:
        all_issues.extend(find_issues(b))

    if not all_issues:
        print("⚠ No readable issues detected.")
        return

    headers = ["File", "Rule", "Severity", "Message"]

    # -------- DOCX --------
    doc = Document()
    doc.add_heading("AI GenOps Security Analysis Report", level=1)

    table = doc.add_table(rows=1, cols=len(headers))
    for i, h in enumerate(headers):
        table.rows[0].cells[i].text = h

    for i in all_issues:
        row = table.add_row().cells
        for idx, h in enumerate(headers):
            row[idx].text = clean(i.get(h))

    doc.save(docx_out)

    # -------- PDF --------
    styles = getSampleStyleSheet()
    elements = [Paragraph("AI GenOps Security Analysis Report", styles["Title"]), Spacer(1, 10)]

    pdf_data = [headers]
    for i in all_issues:
        pdf_data.append([clean(i.get(h)) for h in headers])

    t = Table(pdf_data, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
        ('GRID', (0,0), (-1,-1), 0.25, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    elements.append(t)
    SimpleDocTemplate(str(pdf_out)).build(elements)

    print("✔ Readable DOCX & PDF report created")
