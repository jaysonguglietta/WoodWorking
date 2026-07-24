#!/usr/bin/env python3
import re
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
release=ROOT/"release"
pdfs=list(release.glob("*.pdf"))
assert len(pdfs)==5
report=[]
for p in sorted(pdfs):
    reader=PdfReader(str(p))
    text="\n".join((page.extract_text() or "") for page in reader.pages)
    assert len(reader.pages)>0 and len(text)>200, f"{p.name}: insufficient searchable text"
    assert not re.search(r"\b(TODO|TBD|Lorem ipsum|insert image|placeholder)\b", text, re.I)
    report.append(f"- {p.name}: {len(reader.pages)} pages; searchable text PASS; prohibited strings PASS")
manual=PdfReader(str(release/"DC-1916-001_Illustrated_Shop_Manual_Print.pdf"))
assert 45 <= len(manual.pages) <= 70, f"manual page target missed: {len(manual.pages)}"
(ROOT/"build/reports/pdf-inspection.md").write_text("# PDF Inspection\n\n"+"\n".join(report)+"\n")
print("PASS: PDF count, searchable text, page target, and prohibited strings")

