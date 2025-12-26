#!/usr/bin/env python3
import json
import sys
from pathlib import Path

def render(value, indent=0):
    pad = "  " * indent

    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            lines.append(f"{pad}- **{k}**:")
            lines.extend(render(v, indent + 1))
        return lines

    elif isinstance(value, list):
        lines = []
        for i, item in enumerate(value):
            lines.append(f"{pad}- item {i + 1}:")
            lines.extend(render(item, indent + 1))
        return lines

    else:
        return [f"{pad}- {value}"]

def json_to_markdown(json_path, md_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    md_lines = [
        f"# 📄 JSON to Markdown Report",
        "",
        f"**Source file:** `{json_path.name}`",
        "",
        "---",
        ""
    ]

    md_lines.extend(render(data))

    md_path.write_text("\n".join(md_lines), encoding="utf-8")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: json_to_md.py <input.json> <output.md>")
        sys.exit(1)

    json_file = Path(sys.argv[1])
    md_file = Path(sys.argv[2])

    json_to_markdown(json_file, md_file)
    print(f"✔ Converted {json_file} → {md_file}")
