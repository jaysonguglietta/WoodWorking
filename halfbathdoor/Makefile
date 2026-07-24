PYTHON ?= python3
POPPLER_BIN ?=

.PHONY: all validate preview clean release sources

all: sources
	$(PYTHON) scripts/build_project.py build
	$(PYTHON) scripts/build_quick_guide.py
	$(PYTHON) scripts/package_release.py

.PHONY: quick-guide
quick-guide: sources
	$(PYTHON) scripts/build_quick_guide.py
	$(PYTHON) scripts/package_release.py

sources:
	$(PYTHON) scripts/build_project.py sources

validate: sources
	$(PYTHON) scripts/validate_spec.py
	$(PYTHON) scripts/validate_dimensions.py
	$(PYTHON) scripts/validate_domino_layout.py
	$(PYTHON) scripts/validate_links.py
	$(PYTHON) scripts/validate_images.py
	$(PYTHON) -m unittest discover -s tests -v

preview: all
	POPPLER_BIN="$(POPPLER_BIN)" sh scripts/render_pdf_pages.sh

release: validate all preview
	$(PYTHON) scripts/inspect_pdf.py
	$(PYTHON) scripts/package_release.py

clean:
	$(PYTHON) scripts/build_project.py clean
