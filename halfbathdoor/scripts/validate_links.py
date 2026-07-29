#!/usr/bin/env python3
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
bad=[]
markdown_files=[]
for folder in ["manuscript","project","quick-guide","moulding-guide","cabinetmakers-guide"]:
    markdown_files.extend((ROOT/folder).glob("*.md"))
for p in markdown_files:
    text=p.read_text()
    for link in re.findall(r"\]\((?!https?://)([^)]+)\)", text):
        if not (p.parent/link).resolve().exists(): bad.append((p.name,link))
assert not bad, f"broken local links: {bad}"
print("PASS: local manuscript, project, and companion-guide links")
