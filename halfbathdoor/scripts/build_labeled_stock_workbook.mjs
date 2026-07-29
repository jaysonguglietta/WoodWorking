#!/usr/bin/env node
/**
 * Build the editable Rev. G / LS-05 no-resaw door-only stock workbook.
 *
 * The caller supplies Workbook and SpreadsheetFile from @oai/artifact-tool.
 */

import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT_DIR = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(SCRIPT_DIR, "..");
const PLAN_PATH = path.join(ROOT, "project", "labeled-stock-plan.json");
const SPEC_PATH = path.join(ROOT, "project", "specification.yaml");
const OUTPUT_DIR = path.join(ROOT, "outputs", "labeled-stock-2026-07-26");
const PREVIEW_DIR = path.join(OUTPUT_DIR, "previews");
const RELEASE_DIR = path.join(ROOT, "release");
const FILE_NAME = "DC-1916-001_Labeled_Stock_Cut_Sheet.xlsx";

const COLORS = {
  navy: "#173A56",
  teal: "#2E6F73",
  oak: "#9A6B2F",
  paleOak: "#F4F0E8",
  paleBlue: "#EAF1F5",
  paleGreen: "#EAF2EC",
  paleRed: "#F7E9E7",
  paleAmber: "#FFF4D6",
  red: "#A33B32",
  green: "#3D7452",
  ink: "#20272D",
  gray: "#65717A",
  rule: "#B9C2C7",
  white: "#FFFFFF",
};

function columnName(index) {
  let value = index + 1;
  let result = "";
  while (value > 0) {
    const remainder = (value - 1) % 26;
    result = String.fromCharCode(65 + remainder) + result;
    value = Math.floor((value - 1) / 26);
  }
  return result;
}

function setColumnWidths(sheet, widths, lastRow) {
  widths.forEach((width, index) => {
    const column = columnName(index);
    sheet.getRange(`${column}1:${column}${lastRow}`).format.columnWidth = width;
  });
}

function titleBand(sheet, address, text) {
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[text]];
  range.format = {
    fill: COLORS.navy,
    font: { name: "Aptos Display", size: 20, bold: true, color: COLORS.white },
    verticalAlignment: "center",
    horizontalAlignment: "left",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.navy },
  };
  range.format.rowHeight = 28;
}

function noteBand(sheet, address, text, fill = COLORS.paleBlue, color = COLORS.ink) {
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[text]];
  range.format = {
    fill,
    font: { name: "Aptos", size: 10, bold: true, color },
    verticalAlignment: "center",
    horizontalAlignment: "left",
    wrapText: true,
    borders: { preset: "outside", style: "thin", color: COLORS.rule },
  };
}

function sectionHeader(sheet, address, text, fill = COLORS.teal) {
  const range = sheet.getRange(address);
  range.merge();
  range.values = [[text]];
  range.format = {
    fill,
    font: { name: "Aptos", size: 11, bold: true, color: COLORS.white },
    verticalAlignment: "center",
    horizontalAlignment: "left",
    borders: { preset: "outside", style: "thin", color: fill },
  };
  range.format.rowHeight = 20;
}

function styleHeader(sheet, address, fill = COLORS.navy) {
  sheet.getRange(address).format = {
    fill,
    font: { name: "Aptos", size: 9, bold: true, color: COLORS.white },
    verticalAlignment: "center",
    horizontalAlignment: "left",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.rule },
  };
}

function styleBody(sheet, address) {
  sheet.getRange(address).format = {
    font: { name: "Aptos", size: 9, color: COLORS.ink },
    verticalAlignment: "top",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.rule },
  };
}

function addTable(sheet, address, name, style = "TableStyleMedium2") {
  const table = sheet.tables.add(address, true, name);
  table.style = style;
  table.showHeaders = true;
  table.showFilterButton = true;
  table.showBandedColumns = false;
  return table;
}

function statusFill(status) {
  const upper = String(status).toUpperCase();
  if (upper.includes("STOP") || upper.includes("HOLD") || upper.includes("CRITICAL")) {
    return COLORS.paleRed;
  }
  if (upper.includes("CONDITIONAL")) return COLORS.paleAmber;
  if (upper.includes("RESERVE")) return COLORS.paleBlue;
  if (upper.includes("PASS") || upper.includes("ALLOCATED")) return COLORS.paleGreen;
  return COLORS.paleOak;
}

function opCutLength(operation, kerf) {
  return operation.segment_count * operation.segment_length + operation.crosscuts * kerf;
}

function validateSources(plan, spec) {
  if (plan.document.revision !== "Rev. G" || spec.project.revision !== "Rev. G") {
    throw new Error("Workbook builder requires project Rev. G");
  }
  if (plan.document.stock_plan !== "LS-05" || plan.document.supersedes !== "LS-04") {
    throw new Error("Workbook builder requires LS-05 superseding LS-04");
  }
  if (plan.purchase_requirements.length !== 0 || plan.purchase_summary.planning_quantity_bf !== 0) {
    throw new Error("LS-05 must not release a general door-lumber purchase");
  }
  if (
    spec.opening.clear_width !== 24 ||
    spec.opening.clear_height !== 81 ||
    spec.opening.hinge_side_reveal !== 0.125 ||
    spec.opening.lock_side_reveal !== 0.125 ||
    spec.opening.head_reveal !== 0.125 ||
    spec.opening.bottom_gap !== 0.375 ||
    spec.slab.finished_width !== 23.75 ||
    spec.slab.finished_height !== 80.5 ||
    spec.milling.prefit_assembly_width !== 23.875 ||
    spec.milling.prefit_assembly_height !== 80.625 ||
    spec.frame.stile_width !== 4.25 ||
    spec.frame.rail_shoulder_length !== 15.25
  ) {
    throw new Error("Unexpected Rev. G fitted-door geometry");
  }
  const labels = plan.inventory.map((item) => item.label).join("");
  if (labels !== "ABCDEFGHIJKLMNO") throw new Error(`Expected A-O inventory, got ${labels}`);
  const inventoryByLabel = new Map(plan.inventory.map((item) => [item.label, item]));
  const layersByPart = new Map(plan.laminated_member_schedule.map((item) => [item.part, item]));
  if (
    inventoryByLabel.get("A")?.length !== 72.75 ||
    !String(inventoryByLabel.get("A")?.condition).includes("6-inch damaged section")
  ) {
    throw new Error("Workbook requires STOCK-A current usable length of 72-3/4 inches after damage removal");
  }
  if (inventoryByLabel.get("L")?.width !== 6) {
    throw new Error("Workbook requires STOCK-L current width of 6 inches after edge cleanup");
  }
  if (
    inventoryByLabel.get("G")?.thickness !== 0.9375 ||
    inventoryByLabel.get("G")?.width !== 4.5 ||
    inventoryByLabel.get("G")?.length !== 75 ||
    !String(inventoryByLabel.get("G")?.condition).includes("S4S")
  ) {
    throw new Error("Workbook requires STOCK-G S4S at 15/16 x 4-1/2 x 75");
  }
  if (
    inventoryByLabel.get("M")?.thickness !== 0.75 ||
    inventoryByLabel.get("M")?.width !== 8.25 ||
    inventoryByLabel.get("M")?.length !== 99 ||
    !String(inventoryByLabel.get("M")?.condition).includes("finished white oak")
  ) {
    throw new Error("Workbook requires STOCK-M finished 3/4 x 8-1/4 x 99 white-oak stock");
  }
  for (const label of ["N", "O"]) {
    const row = inventoryByLabel.get(label);
    if (
      row?.thickness !== 1.75 ||
      row?.width !== 11 ||
      row?.length !== 74 ||
      !String(row?.condition).includes("Finished white oak")
    ) {
      throw new Error(`Workbook requires STOCK-${label} finished white oak at 1-3/4 x 11 x 74`);
    }
  }
  const upperPanel = plan.component_allocations.find((item) => item.part === "D-101H");
  if (upperPanel?.stock !== "M" || upperPanel?.allocation !== "M-01; CHK-P-01") {
    throw new Error("Workbook requires STOCK-M as the primary D-101H source");
  }
  if (
    layersByPart.get("D-101D")?.core_stock !== "L-DW-CORE + L-DN-CORE" ||
    layersByPart.get("D-101F")?.core_stock !== "L-F1-CORE + J-F2-CORE"
  ) {
    throw new Error("Workbook requires the revised J/L core swap");
  }
  const moulding = new Map(plan.moulding_purchase_requirements.map((item) => [item.id, item.quantity]));
  if (moulding.get("BUY-MOULD-4Q") !== "7 boards" || moulding.get("BUY-MOULD-6Q") !== "2 boards") {
    throw new Error("Separate moulding order must be 7 x 4/4 and 2 x 6/4 boards");
  }
  const a = plan.assumptions;
  if (
    a.frame_face_preglue_thickness !== 0.3125 ||
    a.frame_core_preglue_thickness !== 0.875 ||
    a.frame_glue_blank_thickness !== 1.5 ||
    a.frame_face_finished_thickness !== 0.25 ||
    a.frame_finished_thickness !== 1.375
  ) {
    throw new Error("Unexpected balanced laminate section");
  }
}

export async function buildLabeledStockWorkbook({ Workbook, SpreadsheetFile }) {
  const plan = JSON.parse(await fs.readFile(PLAN_PATH, "utf8"));
  const spec = JSON.parse(await fs.readFile(SPEC_PATH, "utf8"));
  validateSources(plan, spec);

  const kerf = plan.assumptions.saw_kerf;
  const workbook = Workbook.create();
  const summary = workbook.worksheets.add("Summary");
  const inventory = workbook.worksheets.add("Inventory");
  const cutPlan = workbook.worksheets.add("Cut Plan");
  const checks = workbook.worksheets.add("Checks");
  for (const sheet of [summary, inventory, cutPlan, checks]) sheet.showGridLines = false;

  // Summary
  titleBand(summary, "A1:H2", `DC-1916-001 · Door-Only Stock Plan · ${plan.document.stock_plan}`);
  noteBand(
    summary,
    "A3:H4",
    "CONTROLLED RESERVE / NO-RESAW RELEASE. G is confirmed S4S at 15/16 x 4-1/2 x 75; thickness/width/length fit D-101J. CHK-P-01 still controls clear yield. M carries the upper panel; keep A intact. Keep N/O full. Prove B/C/I/K and J's 6-1/2-in F-core envelope.",
    COLORS.paleRed,
    COLORS.red,
  );
  summary.getRange("A6:B18").values = [
    ["Project", plan.document.project],
    ["Revision", plan.document.revision],
    ["Stock plan", plan.document.stock_plan],
    ["Supersedes", plan.document.supersedes],
    ["Confirmed jamb", "24 x 81 in clear"],
    ["Prefit assembly", "23-7/8 x 80-5/8 x 1-3/8 in"],
    ["Finished fitted slab", "23-3/4 x 80-1/2 x 1-3/8 in"],
    ["Reveals / bottom gap", "1/8 both sides + 1/8 head / 3/8 bottom"],
    ["Saw kerf", kerf],
    ["Measurement basis", "A = 72-3/4 in; B-F/H-K rough; G = S4S 15/16 x 4-1/2 x 75; L = 6 in wide; M = 3/4 x 8-1/4 x 99 finished; N/O = 1-3/4 x 11 x 74 finished white oak"],
    ["Door lumber purchase", plan.purchase_summary.status],
    ["Moulding source", "Separate purchased S4S oak; no A-O credit"],
    ["Current cut release", "G SIZE PASS · CHK-P-01 still controls G; prove B/C/I/K, revised J/L, and M/H; only M/D/G/H are first-stage cut candidates; keep A/N/O reserve"],
  ];
  summary.getRange("A6:A18").format = {
    fill: COLORS.navy,
    font: { name: "Aptos", size: 9, bold: true, color: COLORS.white },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.rule },
  };
  summary.getRange("B6:B18").format = {
    fill: COLORS.paleBlue,
    font: { name: "Aptos", size: 9, color: COLORS.ink },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.rule },
  };
  summary.getRange("B14").format.numberFormat = "# ??/??";

  sectionHeader(summary, "D6:H6", "Balanced frame section");
  summary.getRange("D7:H11").values = [
    ["Layer", "Preglue T", "Finished T", "Operation", "Control"],
    ["Show face", plan.assumptions.frame_face_preglue_thickness, plan.assumptions.frame_face_finished_thickness, "Remove 1/16 after cure", "Long grain"],
    ["Core", plan.assumptions.frame_core_preglue_thickness, plan.assumptions.frame_core_preglue_thickness, "Preserve full thickness", "Continuous through machining"],
    ["Back face", plan.assumptions.frame_face_preglue_thickness, plan.assumptions.frame_face_finished_thickness, "Remove 1/16 after cure", "Long grain"],
    ["TOTAL", plan.assumptions.frame_glue_blank_thickness, plan.assumptions.frame_finished_thickness, "Surface symmetrically", "Machine after lamination"],
  ];
  styleHeader(summary, "D7:H7", COLORS.oak);
  styleBody(summary, "D8:H11");
  summary.getRange("E8:F11").format.numberFormat = "# ??/??";
  summary.getRange("D11:H11").format.fill = COLORS.paleGreen;

  sectionHeader(summary, "D13:H13", "Plan snapshot");
  summary.getRange("D14:E18").values = [
    ["On-hand boards", null],
    ["Recorded-thickness BF", null],
    ["Door lumber purchase BF", 0],
    ["4/4 moulding boards", 7],
    ["6/4 moulding boards", 2],
  ];
  summary.getRange("E14").formulas = [["=COUNTA('Inventory'!A7:A21)"]];
  summary.getRange("E15").formulas = [["=SUM('Inventory'!F7:F21)"]];
  styleBody(summary, "D14:E18");
  summary.getRange("D14:D18").format.fill = COLORS.paleOak;
  summary.getRange("D14:D18").format.font = { name: "Aptos", size: 9, bold: true, color: COLORS.ink };
  summary.getRange("E15").format.numberFormat = "0.00";

  sectionHeader(summary, "A20:H20", "Separate two-face moulding order");
  summary.getRange("A21:H23").values = [
    ["ID", "Quantity", "Material", "Actual minimum", "Allocation", "", "", ""],
    ...plan.moulding_purchase_requirements.map((item) => [
      item.id, item.quantity, item.material, item.actual_minimum, item.allocation, "", "", "",
    ]),
  ];
  for (const row of [21, 22, 23]) summary.getRange(`E${row}:H${row}`).merge();
  styleHeader(summary, "A21:H21", COLORS.oak);
  styleBody(summary, "A22:H23");
  summary.getRange("A22:H23").format.rowHeight = 58;
  summary.getRange("C22:C23").format.columnWidth = 34;
  summary.getRange("D22:D23").format.columnWidth = 40;
  summary.getRange("E22:E23").format.columnWidth = 54;
  noteBand(
    summary,
    "A25:H27",
    "Sequence rule: acclimate and map every board; prove one continuous staged-planed face from B and C; prove I/K each yield two 4-3/8-inch width-ripped lanes; prove J contains one clear 6-1/2-inch envelope and sign the revised J/L core map; mill panel samples; destructively test the same-layup coupon; transfer D/F seam maps; only then release production cutting.",
    COLORS.paleOak,
    COLORS.ink,
  );
  setColumnWidths(summary, [20, 29, 29, 20, 15, 31, 29, 27], 28);
  summary.getRange("A3:H4").format.rowHeight = 28;
  summary.getRange("A25:H27").format.rowHeight = 28;
  summary.freezePanes.freezeRows(4);

  // Inventory
  titleBand(inventory, "A1:J2", "Owner-Labeled Door Lumber Inventory");
  noteBand(
    inventory,
    "A3:J4",
    "Surface condition is mixed. B-F/H-K remain rough; G is confirmed S4S at 15/16 x 4-1/2 x 75; L has cleaned edges; M/N/O are finished as stated. Record moisture, grain, flatness, defects, and clear yield. A-O remain door-only stock. Keep N/O full. No board is divided through its thickness.",
  );
  inventory.getRange("A6:J6").values = [[
    "Stock", "Current / historical T x W x L", "Recorded T", "Current W", "Current L",
    "Recorded BF", "Condition", "Planned door use", "Disposition", "Verified board status",
  ]];
  inventory.getRange("A7:J21").values = plan.inventory.map((item) => [
    `STOCK-${item.label}`, item.original_entry, item.thickness, item.width, item.length,
    null, item.condition, item.planned_use, item.disposition, "",
  ]);
  inventory.getRange("F7").formulas = [["=IF(OR(C7=\"\",D7=\"\",E7=\"\"),\"\",C7*D7*E7/144)"]];
  inventory.getRange("F7:F21").fillDown();
  addTable(inventory, "A6:J21", "DoorStockInventory");
  styleHeader(inventory, "A6:J6");
  styleBody(inventory, "A7:J21");
  inventory.getRange("C7:E21").format.numberFormat = "# ??/??";
  inventory.getRange("F7:F21").format.numberFormat = "0.00";
  inventory.getRange("J7:J21").format.fill = COLORS.paleAmber;
  inventory.getRange("J7:J21").dataValidation = {
    rule: { type: "list", values: ["HOLD - UNMEASURED", "PASS - MAPPED", "FAIL - REJECT"] },
  };
  plan.inventory.forEach((item, index) => {
    inventory.getRange(`I${7 + index}`).format.fill = statusFill(item.disposition);
  });

  sectionHeader(inventory, "A23:J23", "Operation-level milling verification");
  noteBand(
    inventory,
    "A24:J25",
    "Record the actual minimum clear dimensions and sign the matching gate. A formula can track completion, but the written required-yield statement and the signed physical map control.",
    COLORS.paleAmber,
    COLORS.ink,
  );
  const verifyHeader = 27;
  const verifyStart = 28;
  const verifyEnd = verifyStart + plan.operations.length - 1;
  inventory.getRange(`A${verifyHeader}:J${verifyHeader}`).values = [[
    "Stock", "Operation", "Required yield", "Verified min T", "Verified min W",
    "Verified clear L", "Moisture %", "Shop result", "Calculated release", "Initials / date",
  ]];
  inventory.getRange(`A${verifyStart}:J${verifyEnd}`).values = plan.operations.map((op) => [
    `STOCK-${op.stock}`, `${op.operation_id} · ${op.target}`, op.yield,
    null, null, null, null, "", null, "",
  ]);
  inventory.getRange(`I${verifyStart}`).formulas = [[
    `=IF(OR(D${verifyStart}="",E${verifyStart}="",F${verifyStart}="",G${verifyStart}="",H${verifyStart}=""),"HOLD - ENTER VERIFIED DATA",IF(H${verifyStart}="PASS - SHOP INSPECTION","PASS - VERIFY AGAINST WRITTEN YIELD","FAIL / HOLD"))`,
  ]];
  inventory.getRange(`I${verifyStart}:I${verifyEnd}`).fillDown();
  addTable(inventory, `A${verifyHeader}:J${verifyEnd}`, "MillingVerification");
  styleHeader(inventory, `A${verifyHeader}:J${verifyHeader}`, COLORS.oak);
  styleBody(inventory, `A${verifyStart}:J${verifyEnd}`);
  inventory.getRange(`D${verifyStart}:G${verifyEnd}`).format.numberFormat = "# ??/??";
  inventory.getRange(`D${verifyStart}:H${verifyEnd}`).format.fill = COLORS.paleAmber;
  inventory.getRange(`H${verifyStart}:H${verifyEnd}`).dataValidation = {
    rule: { type: "list", values: ["PASS - SHOP INSPECTION", "HOLD - REWORK", "FAIL - REJECT"] },
  };
  inventory.getRange(`I${verifyStart}:I${verifyEnd}`).conditionalFormats.add("containsText", {
    text: "PASS", format: { fill: COLORS.paleGreen, font: { color: COLORS.green, bold: true } },
  });
  inventory.getRange(`I${verifyStart}:I${verifyEnd}`).conditionalFormats.add("containsText", {
    text: "HOLD", format: { fill: COLORS.paleAmber, font: { color: COLORS.oak, bold: true } },
  });
  inventory.getRange(`I${verifyStart}:I${verifyEnd}`).conditionalFormats.add("containsText", {
    text: "FAIL", format: { fill: COLORS.paleRed, font: { color: COLORS.red, bold: true } },
  });
  setColumnWidths(inventory, [13, 28, 34, 13, 13, 15, 13, 24, 30, 18], verifyEnd + 2);
  inventory.getRange("A7:J21").format.rowHeight = 58;
  inventory.getRange(`A${verifyStart}:J${verifyEnd}`).format.rowHeight = 64;
  inventory.freezePanes.freezeRows(6);

  // Cut Plan
  titleBand(cutPlan, "A1:O2", `${plan.document.stock_plan} Door Operations and Lamination Map`);
  noteBand(
    cutPlan,
    "A3:O4",
    "Length use includes the 1/8-inch planning kerf and each operation's explicit end reserve. Shared-board operations use zero additional reserve where stated. Paper fit never overrides actual clear squared-end yield.",
  );
  cutPlan.getRange("A6:O6").values = [[
    "Stock", "Seq", "Op ID", "Target", "Qty", "Segment L", "Crosscuts", "Kerf",
    "Cuts + kerfs", "End reserve", "Total planned", "Rip / milling plan",
    "Required yield", "Status", "Notes",
  ]];
  const opStart = 7;
  const opEnd = opStart + plan.operations.length - 1;
  cutPlan.getRange(`A${opStart}:O${opEnd}`).values = plan.operations.map((op) => [
    `STOCK-${op.stock}`, op.sequence, op.operation_id, op.target, op.segment_count,
    op.segment_length, op.crosscuts, kerf, null,
    op.end_reserve ?? plan.assumptions.default_end_trim_reserve, null,
    op.rip_plan, op.yield, op.status, op.notes,
  ]);
  cutPlan.getRange(`I${opStart}`).formulas = [[`=E${opStart}*F${opStart}+G${opStart}*H${opStart}`]];
  cutPlan.getRange(`I${opStart}:I${opEnd}`).fillDown();
  cutPlan.getRange(`K${opStart}`).formulas = [[`=I${opStart}+J${opStart}`]];
  cutPlan.getRange(`K${opStart}:K${opEnd}`).fillDown();
  addTable(cutPlan, `A6:O${opEnd}`, "DoorCutOperations", "TableStyleMedium9");
  styleHeader(cutPlan, "A6:O6");
  styleBody(cutPlan, `A${opStart}:O${opEnd}`);
  cutPlan.getRange(`F${opStart}:K${opEnd}`).format.numberFormat = "# ??/??";
  plan.operations.forEach((op, index) => {
    cutPlan.getRange(`N${opStart + index}`).format.fill = statusFill(op.status);
  });

  const reconHeader = opEnd + 3;
  sectionHeader(cutPlan, `A${reconHeader}:G${reconHeader}`, "Board-length reconciliation");
  const reconTableHeader = reconHeader + 1;
  const usedLabels = [...new Set(plan.operations.map((op) => op.stock))].sort();
  const reconStart = reconTableHeader + 1;
  const reconEnd = reconStart + usedLabels.length - 1;
  cutPlan.getRange(`A${reconTableHeader}:G${reconEnd}`).values = [
    ["Stock", "Available L", "Cuts + kerfs", "End reserves", "Paper remainder", "Paper status", "Physical release"],
    ...usedLabels.map((label) => {
      const board = plan.inventory.find((item) => item.label === label);
      const boardOps = plan.operations.filter((op) => op.stock === label);
      const cuts = boardOps.reduce((sum, op) => sum + opCutLength(op, kerf), 0);
      const endReserve = boardOps.reduce(
        (sum, op) => sum + (op.end_reserve ?? plan.assumptions.default_end_trim_reserve),
        0,
      );
      const remainder = board.length - cuts - endReserve;
      return [
        `STOCK-${label}`, board.length, cuts, endReserve, remainder,
        remainder >= -1e-8 ? "PAPER FIT ONLY" : "OVERALLOCATED", "HOLD",
      ];
    }),
  ];
  addTable(cutPlan, `A${reconTableHeader}:G${reconEnd}`, "BoardLengthReconciliation");
  styleHeader(cutPlan, `A${reconTableHeader}:G${reconTableHeader}`, COLORS.teal);
  styleBody(cutPlan, `A${reconStart}:G${reconEnd}`);
  cutPlan.getRange(`B${reconStart}:E${reconEnd}`).format.numberFormat = "# ??/??";
  cutPlan.getRange(`G${reconStart}:G${reconEnd}`).format.fill = COLORS.paleRed;

  const scheduleHeader = reconEnd + 3;
  sectionHeader(cutPlan, `A${scheduleHeader}:O${scheduleHeader}`, "Balanced laminated-member schedule");
  const scheduleTableHeader = scheduleHeader + 1;
  const scheduleStart = scheduleTableHeader + 1;
  const scheduleEnd = scheduleStart + plan.laminated_member_schedule.length - 1;
  const scheduleSpans = [
    ["A", "A"], ["B", "C"], ["D", "E"], ["F", "G"],
    ["H", "I"], ["J", "K"], ["L", "M"], ["N", "O"],
  ];
  for (let row = scheduleTableHeader; row <= scheduleEnd; row += 1) {
    for (const [start, end] of scheduleSpans) {
      if (start !== end) cutPlan.getRange(`${start}${row}:${end}${row}`).merge();
    }
  }
  const scheduleHeaders = [
    ["A", "Part"], ["B", "Name"], ["D", "Core stock"], ["F", "Show-face stock"],
    ["H", "Back-face stock"], ["J", "Core blank"], ["L", "Face blanks"], ["N", "Seam control"],
  ];
  for (const [column, value] of scheduleHeaders) {
    cutPlan.getRange(`${column}${scheduleTableHeader}`).values = [[value]];
  }
  plan.laminated_member_schedule.forEach((item, index) => {
    const row = scheduleStart + index;
    const values = [
      ["A", item.part], ["B", item.name], ["D", item.core_stock],
      ["F", item.show_face_stock], ["H", item.back_face_stock],
      ["J", item.core_blank], ["L", item.face_blanks], ["N", item.seams],
    ];
    for (const [column, value] of values) cutPlan.getRange(`${column}${row}`).values = [[value]];
  });
  styleHeader(cutPlan, `A${scheduleTableHeader}:O${scheduleTableHeader}`, COLORS.oak);
  styleBody(cutPlan, `A${scheduleStart}:O${scheduleEnd}`);
  setColumnWidths(
    cutPlan,
    [13, 7, 11, 28, 8, 12, 10, 9, 14, 12, 14, 42, 39, 24, 44],
    scheduleEnd + 2,
  );
  cutPlan.getRange(`A${opStart}:O${opEnd}`).format.rowHeight = 54;
  cutPlan.getRange(`A${scheduleStart}:O${scheduleEnd}`).format.rowHeight = 48;
  cutPlan.freezePanes.freezeRows(6);

  // Checks
  titleBand(checks, "A1:H2", `${plan.document.stock_plan} Physical Release Checks`);
  noteBand(
    checks,
    "A3:H4",
    "Every gate starts on HOLD. Approval must be based on measurements, a signed nesting or seam map, and destructive same-layup coupons—not the reported raw dimensions.",
    COLORS.paleRed,
    COLORS.red,
  );
  checks.getRange("A6:H6").values = [[
    "Gate", "Severity", "Check", "Pass condition", "Fallback", "Formula status", "Gate approval", "Initials / date",
  ]];
  const gateStart = 7;
  const gateEnd = gateStart + plan.critical_checks.length - 1;
  checks.getRange(`A${gateStart}:H${gateEnd}`).values = plan.critical_checks.map((item) => [
    item.id, item.severity, item.check, item.pass, item.fallback,
    "HOLD - SHOP APPROVAL REQUIRED", "", "",
  ]);
  addTable(checks, `A6:H${gateEnd}`, "LS05ReleaseChecks", "TableStyleMedium3");
  styleHeader(checks, "A6:H6", COLORS.oak);
  styleBody(checks, `A${gateStart}:H${gateEnd}`);
  checks.getRange(`F${gateStart}:F${gateEnd}`).format = {
    fill: COLORS.paleRed,
    font: { name: "Aptos", size: 9, bold: true, color: COLORS.red },
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: COLORS.rule },
  };
  checks.getRange(`G${gateStart}:G${gateEnd}`).format.fill = COLORS.paleAmber;
  checks.getRange(`G${gateStart}:G${gateEnd}`).dataValidation = {
    rule: { type: "list", values: ["HOLD", "APPROVED", "REJECTED"] },
  };

  const typoHeader = gateEnd + 3;
  sectionHeader(checks, `A${typoHeader}:H${typoHeader}`, "Measurement and notation review");
  const typoTableHeader = typoHeader + 1;
  const typoStart = typoTableHeader + 1;
  const typoEnd = typoStart + plan.typo_review.length - 1;
  checks.getRange(`A${typoTableHeader}:C${typoEnd}`).values = [
    ["Entry", "Assessment", "Required action before cutting"],
    ...plan.typo_review.map((item) => [item.entry, item.assessment, item.action]),
  ];
  addTable(checks, `A${typoTableHeader}:C${typoEnd}`, "MeasurementReview");
  styleHeader(checks, `A${typoTableHeader}:C${typoTableHeader}`, COLORS.teal);
  styleBody(checks, `A${typoStart}:C${typoEnd}`);

  const mouldHeader = typoEnd + 3;
  sectionHeader(checks, `A${mouldHeader}:H${mouldHeader}`, "Separate moulding purchase verification");
  const mouldTableHeader = mouldHeader + 1;
  const mouldStart = mouldTableHeader + 1;
  const mouldEnd = mouldStart + plan.moulding_purchase_requirements.length - 1;
  checks.getRange(`A${mouldTableHeader}:F${mouldEnd}`).values = [
    ["ID", "Quantity", "Material", "Actual minimum", "Allocation", "Shop check"],
    ...plan.moulding_purchase_requirements.map((item) => [
      item.id, item.quantity, item.material, item.actual_minimum, item.allocation, "",
    ]),
  ];
  addTable(checks, `A${mouldTableHeader}:F${mouldEnd}`, "MouldingPurchaseCheck");
  styleHeader(checks, `A${mouldTableHeader}:F${mouldTableHeader}`, COLORS.oak);
  styleBody(checks, `A${mouldStart}:F${mouldEnd}`);
  checks.getRange(`F${mouldStart}:F${mouldEnd}`).format.fill = COLORS.paleAmber;
  checks.getRange(`F${mouldStart}:F${mouldEnd}`).dataValidation = {
    rule: { type: "list", values: ["NOT BOUGHT", "IN HAND - VERIFIED", "REJECTED"] },
  };

  const finalNote = mouldEnd + 2;
  noteBand(
    checks,
    `A${finalNote}:H${finalNote + 2}`,
    "CONTROLLED-RESERVE STOP. Measure yield after each board and before processing the next. If B/C/I/K, M, or H fails, stop and remap; never shorten or splice a stile. Keep A intact unless M fails; keep N/O full unless a signed short-core fallback is released. Do not transfer A-O remnants to moulding.",
    COLORS.paleAmber,
    COLORS.ink,
  );
  const checksLastRow = finalNote + 2;
  setColumnWidths(checks, [17, 13, 44, 48, 42, 29, 18, 18], checksLastRow + 2);
  checks.getRange(`A${gateStart}:H${gateEnd}`).format.rowHeight = 82;
  checks.getRange(`A${typoStart}:C${typoEnd}`).format.rowHeight = 142;
  checks.getRange(`A${mouldStart}:F${mouldEnd}`).format.rowHeight = 64;
  checks.freezePanes.freezeRows(6);

  // Inspect, render, and export.
  await fs.mkdir(PREVIEW_DIR, { recursive: true });
  await fs.mkdir(RELEASE_DIR, { recursive: true });
  const summaryInspection = await workbook.inspect({
    kind: "table",
    range: "Summary!A1:H27",
    include: "values,formulas",
    tableMaxRows: 30,
    tableMaxCols: 10,
    maxChars: 14000,
  });
  console.log(summaryInspection.ndjson);
  const cutInspection = await workbook.inspect({
    kind: "table",
    range: `Cut Plan!A1:O${scheduleEnd}`,
    include: "values,formulas",
    tableMaxRows: 55,
    tableMaxCols: 16,
    maxChars: 18000,
  });
  console.log(cutInspection.ndjson);
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  console.log(errors.ndjson);

  const renderRanges = {
    Summary: "A1:H27",
    Inventory: `A1:J${verifyEnd}`,
    "Cut Plan": `A1:O${scheduleEnd}`,
    Checks: `A1:H${checksLastRow}`,
  };
  for (const [sheetName, range] of Object.entries(renderRanges)) {
    const preview = await workbook.render({ sheetName, range, scale: 1.5, format: "png" });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    await fs.writeFile(
      path.join(PREVIEW_DIR, `${sheetName.toLowerCase().replaceAll(" ", "-")}.png`),
      bytes,
    );
  }

  const workbookFile = await SpreadsheetFile.exportXlsx(workbook);
  const outputPath = path.join(OUTPUT_DIR, FILE_NAME);
  const releasePath = path.join(RELEASE_DIR, FILE_NAME);
  await workbookFile.save(outputPath);
  await fs.copyFile(outputPath, releasePath);
  console.log(`PASS: built ${outputPath}, copied release workbook, and rendered all four sheets`);
}
