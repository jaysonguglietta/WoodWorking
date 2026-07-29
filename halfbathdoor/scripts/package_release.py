#!/usr/bin/env python3
import csv
import hashlib
import re
import zipfile
from pathlib import Path
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[1]
release=ROOT/"release"


def refresh_source_archive(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as source_zip:
        for item in sorted(ROOT.rglob("*")):
            relative = item.relative_to(ROOT)
            if (
                item.is_dir()
                or release in item.parents
                or (ROOT/"build") in item.parents
                or relative.parts[0] in {"output", "outputs"}
                or "tmp" in relative.parts
                or "__pycache__" in item.parts
                or ".git" in item.parts
                or item.name == ".DS_Store"
            ):
                continue
            source_zip.write(item, Path("halfbathdoor")/relative)


refresh_source_archive(release/"DC-1916-001_Source_Project.zip")
required=[
"DC-1916-001_Illustrated_Shop_Manual_Print.pdf","DC-1916-001_Illustrated_Shop_Manual_Screen.pdf",
"DC-1916-001_Printable_Templates.pdf","DC-1916-001_Illustrated_Shop_Manual.html",
"DC-1916-001_Quick_Cut_and_Assembly_Guide.pdf","DC-1916-001_Quick_Cut_and_Assembly_Guide.md",
"DC-1916-001_Visual_Assembly_Guide.pdf",
"DC-1916-001_Five_Panel_Door_Project_Plans.pdf",
"DC-1916-001_Custom_Moulding_Shop_Manual.pdf","DC-1916-001_Custom_Moulding_Shop_Manual.md",
"DC-1916-001_Cabinetmakers_Builder_Guide.pdf","DC-1916-001_Cabinetmakers_Builder_Guide.md",
"DC-1916-001_Door_Shopping_List.pdf","DC-1916-001_Door_Shopping_List.md",
"DC-1916-001_Labeled_Stock_Cut_Sheet.pdf","DC-1916-001_Labeled_Stock_Cut_Sheet.md",
"DC-1916-001_Labeled_Stock_Cut_Sheet.csv","DC-1916-001_Labeled_Stock_Cut_Sheet.xlsx",
"DC-1916-001_Rough_Length_Cut_List.pdf","DC-1916-001_Rough_Length_Cut_List.md",
"DC-1916-001_Rough_Length_Cut_List.csv",
"DC-1916-001_Buy_List.csv","DC-1916-001_Cut_List.csv","DC-1916-001_Domino_Setup_Register.csv",
"DC-1916-001_Moulding_Drawings.pdf","DC-1916-001_Moulding_Cut_List.csv",
"DC-1916-001_Moulding_Field_Measurement_Worksheet.pdf","DC-1916-001_Specification.yaml",
"DC-1916-001_Source_Project.zip","DC-1916-001_Build_Report.md"]
for name in required: assert (release/name).stat().st_size>100, name

workbook=release/"DC-1916-001_Labeled_Stock_Cut_Sheet.xlsx"
with zipfile.ZipFile(workbook) as workbook_zip:
    workbook_members=set(workbook_zip.namelist())
    workbook_xml=" ".join(
        workbook_zip.read(name).decode("utf-8", errors="ignore")
        for name in workbook_members
        if name.endswith(".xml")
    ).lower()
for member in {"[Content_Types].xml","xl/workbook.xml"}:
    assert member in workbook_members, f"labeled-stock workbook missing {member}"
for term in {"rev. g","ls-05","no-resaw","4-3/8","s4s","15/16","4-1/2 x 75","chk-p-01"}:
    assert term in workbook_xml, f"labeled-stock workbook missing current control {term}"
for stale in {"stile resaw and core gates","ls-04 door operations"}:
    assert stale not in workbook_xml, f"labeled-stock workbook retains stale control {stale}"

build_report=(release/"DC-1916-001_Build_Report.md").read_text(encoding="utf-8")
assert re.search(r"labeled[- ]stock[- ]cut[- ]sheet",build_report,re.I), "build report omits labeled-stock cut sheet"
assert re.search(r"rough[- ]length[- ]cut[- ]list",build_report,re.I), "build report omits rough-length cut list"
controlled_pdf_names=[name for name in required if name.lower().endswith(".pdf")]
actual_pdf_pages=sum(len(PdfReader(str(release/name)).pages) for name in controlled_pdf_names)
report_total=re.search(r"total controlled pdf pages:\s*(\d+)\b",build_report,re.I)
assert report_total and int(report_total.group(1))==actual_pdf_pages, (
    f"build report controls {report_total.group(1) if report_total else 'no'} pages; "
    f"actual controlled total is {actual_pdf_pages}"
)
visual_qc=(ROOT/"build/reports/visual-qc.md").read_text(encoding="utf-8")
assert re.search(r"labeled[- ]stock[- ]cut[- ]sheet",visual_qc,re.I), "visual-QC report omits labeled-stock cut sheet"
assert re.search(r"rough[- ]length[- ]cut[- ]list",visual_qc,re.I), "visual-QC report omits rough-length cut list"
visual_total=re.search(r"metadata lists\s*(\d+)\s*pages\b",visual_qc,re.I)
assert visual_total and int(visual_total.group(1))==actual_pdf_pages, (
    f"visual-QC report accounts for {visual_total.group(1) if visual_total else 'no'} pages; "
    f"actual controlled total is {actual_pdf_pages}"
)

register=ROOT/"project"/"cabinetmakers-render-register.csv"
with register.open(newline="",encoding="utf-8") as handle:
    render_rows=list(csv.DictReader(handle))
assert len(render_rows)==27, f"expected 27 cabinetmaker renderings, got {len(render_rows)}"
render_slugs=[row["Slug"] for row in render_rows]
assert len(render_slugs)==len(set(render_slugs)), "duplicate cabinetmaker rendering slug"

archive=release/"DC-1916-001_Source_Project.zip"
with zipfile.ZipFile(archive) as source_zip:
    archived=set(source_zip.namelist())
prefix="halfbathdoor/"
assert not any(
    len(Path(name).parts) > 1 and Path(name).parts[1] in {"output", "outputs"}
    for name in archived
), "source archive contains generated output directories"
source_required={
    prefix+"cabinetmakers-guide/DC-1916-001_Cabinetmakers_Builder_Guide.md",
    prefix+"project/cabinetmakers-render-register.csv",
    prefix+"scripts/build_cabinetmakers_guide.py",
    prefix+"scripts/build_flatpack_visual_guide.py",
    prefix+"scripts/build_project_plans_booklet.py",
    prefix+"project-plans/DC-1916-001_Five_Panel_Door_Project_Plans.md",
    prefix+"scripts/generate_cabinetmakers_3d.py",
    prefix+"scripts/build_door_shopping_list.py",
    prefix+"shopping-list/DC-1916-001_Door_Shopping_List.md",
    prefix+"project/labeled-stock-plan.json",
    prefix+"scripts/build_labeled_stock_cut_sheet.py",
    prefix+"scripts/build_labeled_stock_workbook.mjs",
    prefix+"stock-plan/DC-1916-001_Labeled_Stock_Cut_Sheet.md",
    prefix+"project/rough-length-cut-plan.json",
    prefix+"scripts/build_rough_length_cut_list.py",
    prefix+"stock-plan/DC-1916-001_Rough_Length_Cut_List.md",
}
for slug in render_slugs:
    source_required.add(prefix+f"cabinetmakers-guide/renderings/{slug}.svg")
    source_required.add(prefix+f"cabinetmakers-guide/renderings/{slug}.png")
missing_source=sorted(source_required-archived)
assert not missing_source, f"source archive missing controlled source files: {missing_source}"
local_source_paths={
    prefix+"project/labeled-stock-plan.json": ROOT/"project/labeled-stock-plan.json",
    prefix+"scripts/build_labeled_stock_cut_sheet.py": ROOT/"scripts/build_labeled_stock_cut_sheet.py",
    prefix+"scripts/build_labeled_stock_workbook.mjs": ROOT/"scripts/build_labeled_stock_workbook.mjs",
    prefix+"stock-plan/DC-1916-001_Labeled_Stock_Cut_Sheet.md": ROOT/"stock-plan/DC-1916-001_Labeled_Stock_Cut_Sheet.md",
    prefix+"project/rough-length-cut-plan.json": ROOT/"project/rough-length-cut-plan.json",
    prefix+"scripts/build_rough_length_cut_list.py": ROOT/"scripts/build_rough_length_cut_list.py",
    prefix+"stock-plan/DC-1916-001_Rough_Length_Cut_List.md": ROOT/"stock-plan/DC-1916-001_Rough_Length_Cut_List.md",
}
with zipfile.ZipFile(archive) as source_zip:
    for archived_name,local_path in local_source_paths.items():
        assert source_zip.read(archived_name)==local_path.read_bytes(), f"source archive has stale {archived_name}"
assert not any(Path(name).name==".DS_Store" for name in archived), "source archive contains .DS_Store"

lines=[f"{hashlib.sha256((release/n).read_bytes()).hexdigest()}  {n}" for n in sorted(required)]
(release/"SHA256SUMS.txt").write_text("\n".join(lines)+"\n")
print(f"PASS: {len(required)} release artifacts and checksums")
