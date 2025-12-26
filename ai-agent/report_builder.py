import json
import pandas as pd
from bs4 import BeautifulSoup
from pathlib import Path


def extract_json_blocks(md_text):
    blocks = []

    for section in md_text.split("<details>")[1:]:
        if "```json" not in section:
            continue

        try:
            json_text = section.split("```json", 1)[1].split("```", 1)[0]
            blocks.append(json.loads(json_text.strip()))
        except Exception:
            continue

    return blocks



def flatten_json(obj, parent_key="", sep="."):
    items = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            items.extend(flatten_json(v, new_key, sep=sep))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            new_key = f"{parent_key}[{i}]"
            items.extend(flatten_json(v, new_key, sep=sep))
    else:
        items.append((parent_key, obj))
    return items


def normalize_block(block, source_index):
    flat = dict(flatten_json(block))
    rowset = []

    issue_keys = [k for k in flat.keys() if "[" in k]

    if not issue_keys:
        flat["source_block"] = source_index
        rowset.append(flat)
        return rowset

    groups = {}
    for key, val in flat.items():
        if "[" in key:
            prefix = key.split("[")[0]
            groups.setdefault(prefix, {})[key] = val
        else:
            for g in groups.values():
                g[key] = val

    for g in groups.values():
        g["source_block"] = source_index
        rowset.append(g)

    return rowset


def build_report(INPUT_MD: str, OUTPUT_CSV: str, OUTPUT_XLSX: str):
    INPUT_MD = Path(INPUT_MD)
    OUTPUT_CSV = Path(OUTPUT_CSV)
    OUTPUT_XLSX = Path(OUTPUT_XLSX)

    md = INPUT_MD.read_text(encoding="utf-8")
    blocks = extract_json_blocks(md)

    all_rows = []
    for i, block in enumerate(blocks):
        all_rows.extend(normalize_block(block, i))

    if not all_rows:
        print("⚠ No JSON blocks found inside <details> tags.")
        return

    df = pd.DataFrame(all_rows)

    df.columns = (
        df.columns
        .str.replace(r"\[\d+\]", "", regex=True)
        .str.replace(".", "_", regex=False)
    )

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_XLSX.parent.mkdir(parents=True, exist_ok=True)

    df.to_csv(OUTPUT_CSV, index=False)
    df.to_excel(OUTPUT_XLSX, index=False)

    print("✔ Universal report generated:")
    print(" -", OUTPUT_CSV)
    print(" -", OUTPUT_XLSX)