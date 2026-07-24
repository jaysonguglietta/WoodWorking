# Project DC-1916-001 Agent Rules

- Treat `project/specification.yaml` as authoritative. It is JSON-formatted YAML so the standard library can validate it.
- Preserve the historically appropriate early-twentieth-century appearance and every permanent component identifier.
- `D-101M` and `D-101N` are the documented resolution of the source brief's four-panel/five-panel conflict; do not remove them without redesigning and revalidating the complete door.
- Keep the Festool Domino DF 500 as the primary frame-joinery tool. Never substitute DF 700 capacities or dimensions.
- Treat the installed jamb as complete and outside fabrication scope.
- Keep diagrams, registers, cut lists, templates, and manuscript dimensions synchronized with the specification.
- Run `make validate` before committing.
- Use SVG for technical dimensions and labels. Keep raster renders free of dense text.
- Inspect every generated PDF page and every generated image.
- Record engineering changes in `project/decisions.md`.
- Distinguish fixed dimensions from completed-jamb, adjacent-trim, floor, and hardware measurements.
- Never leave TODO, TBD, placeholder, or "insert image" text in a release build.
- Never claim completion without building and inspecting the release files.

