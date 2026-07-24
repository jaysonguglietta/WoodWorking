#!/usr/bin/env python3
import hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
release=ROOT/"release"
required=[
"DC-1916-001_Illustrated_Shop_Manual_Print.pdf","DC-1916-001_Illustrated_Shop_Manual_Screen.pdf",
"DC-1916-001_Printable_Templates.pdf","DC-1916-001_Illustrated_Shop_Manual.html",
"DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf","DC-1916-001_Quick_Cut_and_Assembly_Guide.md",
"DC-1916-001_Buy_List.csv","DC-1916-001_Cut_List.csv","DC-1916-001_Domino_Setup_Register.csv",
"DC-1916-001_Moulding_Drawings.pdf","DC-1916-001_Moulding_Cut_List.csv",
"DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf","DC-1916-001_Specification.yaml",
"DC-1916-001_Source_Project.zip","DC-1916-001_Build_Report.md"]
for name in required: assert (release/name).stat().st_size>100, name
lines=[f"{hashlib.sha256((release/n).read_bytes()).hexdigest()}  {n}" for n in sorted(required)]
(release/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n")
print(f"PASS: {len(required)} release artifacts and checksums")
