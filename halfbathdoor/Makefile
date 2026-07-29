PYTHON ?= python3
POPPLER_BIN ?=
STOCK_WORKBOOK ?= outputs/labeled-stock-2026-07-26/DC-1916-001_Labeled_Stock_Cut_Sheet.xlsx

.PHONY: all validate preview clean release sources quick-guide visual-guide project-plans moulding-guide cabinetmakers-guide shopping-list stock-cut-sheet rough-length-cut-list

all: stock-cut-sheet
	$(PYTHON) scripts/build_project.py build
	$(PYTHON) scripts/build_quick_guide.py
	$(PYTHON) scripts/build_flatpack_visual_guide.py
	$(PYTHON) scripts/build_project_plans_booklet.py
	$(PYTHON) scripts/build_moulding_guide.py
	$(PYTHON) scripts/build_cabinetmakers_guide.py
	$(PYTHON) scripts/build_door_shopping_list.py
	$(PYTHON) scripts/package_release.py

quick-guide: stock-cut-sheet
	$(PYTHON) scripts/generate_quick_assembly_diagrams.py
	$(PYTHON) scripts/build_quick_guide.py
	$(PYTHON) scripts/build_flatpack_visual_guide.py
	$(PYTHON) scripts/build_door_shopping_list.py
	$(PYTHON) scripts/package_release.py

visual-guide: sources
	$(PYTHON) scripts/build_flatpack_visual_guide.py

project-plans: sources
	$(PYTHON) scripts/build_project_plans_booklet.py

moulding-guide: stock-cut-sheet
	$(PYTHON) scripts/build_moulding_guide.py
	$(PYTHON) scripts/build_door_shopping_list.py
	$(PYTHON) scripts/package_release.py

cabinetmakers-guide: stock-cut-sheet
	$(PYTHON) scripts/build_project.py build
	$(PYTHON) scripts/build_quick_guide.py
	$(PYTHON) scripts/build_flatpack_visual_guide.py
	$(PYTHON) scripts/build_project_plans_booklet.py
	$(PYTHON) scripts/build_moulding_guide.py
	$(PYTHON) scripts/build_cabinetmakers_guide.py
	$(PYTHON) scripts/build_door_shopping_list.py
	$(PYTHON) scripts/package_release.py

shopping-list: sources
	$(PYTHON) scripts/build_door_shopping_list.py

stock-cut-sheet: sources
	$(PYTHON) scripts/build_labeled_stock_cut_sheet.py
	$(PYTHON) scripts/build_rough_length_cut_list.py
	cp -p "$(STOCK_WORKBOOK)" release/DC-1916-001_Labeled_Stock_Cut_Sheet.xlsx

rough-length-cut-list:
	$(PYTHON) scripts/build_rough_length_cut_list.py

sources:
	$(PYTHON) scripts/build_project.py sources
	$(PYTHON) scripts/generate_quick_assembly_diagrams.py
	$(PYTHON) scripts/generate_moulding_diagrams.py
	$(PYTHON) scripts/generate_cabinetmakers_3d.py

validate: stock-cut-sheet
	$(PYTHON) scripts/validate_spec.py
	$(PYTHON) scripts/validate_dimensions.py
	$(PYTHON) scripts/validate_domino_layout.py
	$(PYTHON) scripts/validate_links.py
	$(PYTHON) scripts/validate_images.py
	$(PYTHON) -m unittest discover -s tests -v

preview: all
	POPPLER_BIN="$(POPPLER_BIN)" sh scripts/render_pdf_pages.sh
	$(PYTHON) scripts/make_contact_sheets.py

release: all validate preview
	$(PYTHON) scripts/inspect_pdf.py
	$(PYTHON) scripts/package_release.py

clean:
	$(PYTHON) scripts/build_project.py clean
