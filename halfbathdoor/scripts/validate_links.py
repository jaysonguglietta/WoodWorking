#!/usr/bin/env python3
import re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
bad=[]
for p in list((ROOT/"manuscript").glob("*.md")) + list((ROOT/"project").glob("*.md")):
    text=p.read_text()
    for link in re.findall(r"\]\((?!https?://)([^)]+)\)", text):
        if not (p.parent/link).resolve().exists(): bad.append((p.name,link))
assert not bad, f"broken local links: {bad}"
print("PASS: local manuscript and project links")

