"""
translate_rub_data.py — Convert RUB SX creep Excel to schema v2.1.8 JSON files.

Source: SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx (Zenodo record 7663974)
Output: One JSON per (orientation, temperature, stress) test.

Usage (from Parsing/ directory, python311 env active):

    # With local file:
    python bin/translate_rub_data.py Data/RUBDataset/SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx

    # Auto-download from Zenodo if file is missing:
    python bin/translate_rub_data.py --download -o Data/RUBDataset_Json

    # With schema validation:
    python bin/translate_rub_data.py Data/RUBDataset/SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx --validate
"""

import argparse
import json
import logging
import os
import re
import sys

logging.basicConfig(level=logging.INFO)
Logger = logging.getLogger(__name__)

_script_dir = os.path.dirname(os.path.abspath(__file__))
_parsing_root = os.path.dirname(_script_dir)
_project_root = os.path.dirname(_parsing_root)

DEFAULT_SCHEMA_FILE = os.path.join(
    _project_root, "Data Schema", "2026-06_Data-Schema_Creep_v2.1.8.json"
)
DEFAULT_OUTPUT_DIR = os.path.join(_parsing_root, "Data", "RUBDataset_Json")
DEFAULT_EXCEL_PATH = os.path.join(
    _parsing_root, "Data", "RUBDataset", "SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx"
)

ZENODO_RECORD_ID = "7663974"
ZENODO_FILE_URL = (
    f"https://zenodo.org/records/{ZENODO_RECORD_ID}/files/"
    "SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx?download=1"
)
ZENODO_CREEP_CURVE_BASE = f"https://zenodo.org/records/{ZENODO_RECORD_ID}/files/"

# Column layout in each orientation sheet: 3 columns per test
_COLS_PER_TEST = 3


# ─── Download ──────────────────────────────────────────────────────────────────

def _download_excel(dest_path: str) -> None:
    """Download the RUB Excel file from Zenodo if not already present."""
    import urllib.request
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    Logger.info("Downloading RUB Excel from Zenodo record %s …", ZENODO_RECORD_ID)
    urllib.request.urlretrieve(ZENODO_FILE_URL, dest_path)
    Logger.info("Saved to: %s", dest_path)


# ─── Excel parsing ─────────────────────────────────────────────────────────────

def _safe_str(value) -> str:
    if value is None or (isinstance(value, float) and value != value):  # NaN
        return ""
    return str(value).strip()


def _parse_rupture_time(metadata_string: str) -> tuple[str, str]:
    """Extract rupture time value and unit from the per-test metadata string.

    The string looks like: "720 C/800 MPa, Rupture time: 78.3 h" or similar.
    Returns ("78.3", "h") or ("", "") if not found.
    """
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*h", metadata_string, re.IGNORECASE)
    if m:
        value = m.group(1).replace(",", ".")
        return value, "h"
    return "", ""


def _parse_overview(sheet) -> dict:
    """Extract global metadata from the Overview sheet.

    Rows (0-indexed) referenced from notebook 02_GetRubTables.ipynb:
      row 0  col 0: TITLE
      row 2-3:      LICENCE (concatenated non-null values at positions 2,3)
      row 18:       HEAT_TREATMENT
      row 21:       PUBLICATION
      row 24:       PREPARATION
      rows 27-28:   EXPERIMENTS (concatenated)
      last 6 rows:  ASSOCIATED_PUBLICATIONS (concatenated)
    """
    col = sheet.iloc[:, 0].fillna("")

    def _get_row(idx: int) -> str:
        try:
            return _safe_str(col.iloc[idx])
        except IndexError:
            return ""

    def _concat_rows(*indices) -> str:
        return " ".join(_safe_str(col.iloc[i]) for i in indices if i < len(col)).strip()

    # Licence: non-null values at positions 2 and 3 of column 0
    licence_vals = sheet.iloc[:, 0].dropna()
    licence = ""
    try:
        idx_list = list(licence_vals.index)
        if len(idx_list) > 3:
            licence = _safe_str(licence_vals.iloc[2]) + " " + _safe_str(licence_vals.iloc[3])
    except Exception:
        pass

    # Associated publications: last 6 non-null entries
    assoc_pubs = ""
    try:
        non_null = sheet.iloc[:, 0].dropna()
        assoc_pubs = " ".join(_safe_str(v) for v in non_null.iloc[-6:])
    except Exception:
        pass

    return {
        "title": _get_row(0),
        "licence": licence.strip(),
        "heat_treatment": _get_row(18),
        "publication": _get_row(21),
        "preparation": _get_row(24),
        "experiments": _concat_rows(27, 28),
        "associated_publications": assoc_pubs,
    }


def _parse_orientation_sheet(sheet, orientation: str) -> list[dict]:
    """Parse one orientation sheet into a list of test dicts.

    Sheet layout (0-indexed rows):
      Rows 0–5: sheet description text (ignored for per-test parsing)
      Row 6:    temperature/stress header per test — e.g. "720/800" in col 3*i
      Row 7:    rupture-time string — e.g. "Rupture time: 971 h" in col 3*i
      Row 8+:   numeric time-series data: col 3*i = time (s), col 3*i+1 = strain

    3 columns per test: col[3*i]=time, col[3*i+1]=strain, col[3*i+2]=separator.
    """
    _HEADER_ROW = 6   # row with "temp/stress" identifiers
    _META_ROW   = 7   # row with rupture-time strings
    _DATA_START = 8   # first row of numeric data

    tests = []
    n_cols = sheet.shape[1]
    n_tables = (n_cols - 1) // _COLS_PER_TEST  # conservative count

    for i in range(n_tables):
        col_t = _COLS_PER_TEST * i       # time column
        col_s = _COLS_PER_TEST * i + 1   # strain column

        if col_t >= n_cols or col_s >= n_cols:
            break

        temp_stress_str = _safe_str(sheet.iat[_HEADER_ROW, col_t])
        meta_str        = _safe_str(sheet.iat[_META_ROW, col_t])

        if "/" not in temp_stress_str:
            continue  # no test here (separator or empty column)

        try:
            temp_str, stress_str = [p.strip() for p in temp_stress_str.split("/", 1)]
            temperature_value = float(temp_str.replace(",", "."))
            stress_value = float(stress_str.replace(",", "."))
        except ValueError:
            Logger.warning("Could not parse temperature/stress from %r — skipping", temp_stress_str)
            continue

        rupture_time_value, rupture_time_unit = _parse_rupture_time(meta_str)
        if rupture_time_value:
            rupture_time_value = float(rupture_time_value)

        # Parse numeric rows from _DATA_START onwards
        times, strains = [], []
        for r in range(_DATA_START, sheet.shape[0]):
            t_raw = sheet.iat[r, col_t]
            s_raw = sheet.iat[r, col_s]
            try:
                t_val = float(str(t_raw).replace(",", "."))
                s_val = float(str(s_raw).replace(",", "."))
                times.append(t_val)
                strains.append(s_val)
            except (ValueError, TypeError):
                break  # end of numeric block

        if not times:
            continue

        tests.append({
            "orientation": orientation.strip(),
            "temperature_value": temperature_value,   # float, °C
            "temperature_unit": "°C",
            "stress_value": stress_value,             # float, MPa
            "stress_unit": "MPa",
            "rupture_time_value": rupture_time_value, # float or "", h
            "rupture_time_unit": rupture_time_unit if rupture_time_unit else "h",
            "times": times,
            "times_unit": "s",
            "strain": strains,
            "strain_unit": "",  # dimensionless (absolute strain)
        })

    return tests


def read_rub_excel(file_path: str) -> tuple[dict, list[dict]]:
    """Parse the RUB Excel file.

    Returns:
        (global_meta, tests)
        global_meta: dict with dataset-level metadata
        tests: list of per-test dicts
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError(
            "pandas is required to parse the RUB Excel file. "
            "Install it with: pip install pandas openpyxl"
        )

    Logger.info("Reading Excel: %s", file_path)
    wb = pd.read_excel(file_path, sheet_name=None, header=None, na_filter=False)

    sheets = {k.strip(): v for k, v in wb.items()}
    Logger.info("Sheets found: %s", list(sheets.keys()))

    overview_sheet = sheets.get("Overview")
    global_meta = _parse_overview(overview_sheet) if overview_sheet is not None else {}

    all_tests = []
    for sheet_name, sheet in sheets.items():
        if sheet_name == "Overview":
            continue
        orientation = sheet_name.strip()
        tests = _parse_orientation_sheet(sheet, orientation)
        Logger.info("  %s: %d tests parsed", orientation, len(tests))
        all_tests.extend(tests)

    Logger.info("Total tests: %d", len(all_tests))
    return global_meta, all_tests


# ─── Schema mapping ────────────────────────────────────────────────────────────

def _orientation_label(sheet_name: str) -> str:
    """Convert sheet name like '001-direction' to crystallographic notation '[001]'."""
    m = re.match(r"(\d{3})", sheet_name.strip())
    return f"[{m.group(1)}]" if m else sheet_name


def _float_to_str(v) -> str:
    """Convert float to string, omitting .0 for whole numbers."""
    if v == "" or v is None:
        return ""
    f = float(v)
    return str(int(f)) if f == int(f) else str(f)


def _make_test_id(test: dict) -> str:
    orient = test["orientation"].replace(" ", "-")
    temp = _float_to_str(test["temperature_value"]).replace(".", "p")
    stress = _float_to_str(test["stress_value"]).replace(".", "p")
    return f"RUB_{orient}_{temp}C_{stress}MPa"


_HEAT_TREATMENT_ANNEALING = (
    "RT (20 °C/min) → 1290 °C for 1 h (1 °C/min) → 1300 °C for 6 h "
    "(150 °C/min) → 800 °C (air cooled) → RT"
)
_HEAT_TREATMENT_AGEING = "1140 °C for 4 h → 870 °C for 16 h → RT"


def translate_rub_test(global_meta: dict, test: dict) -> dict:
    """Map a single RUB test dict to a schema v2.1.8-conforming nested dict."""
    test_id = _make_test_id(test)
    orientation = _orientation_label(test["orientation"])

    doc = {
        "MeasurementData": {
            "AdditionalMetadata": {
                "TestInfo": {
                    "testJobDetails": {
                        "testID": test_id,
                    },
                    "testParameters": {
                        "testStandardApplied": "No",
                        "testStandard": {
                            "testStandardOptions": "Other (Please specify in the comment)",
                            "otherTestStandard": "Not applicable",
                        },
                        "specifiedTemperature": {
                            "value": _float_to_str(test["temperature_value"]),
                            "unit": test["temperature_unit"],
                        },
                        "typeOfLoading": "Tension",
                        "loadControlType": "Constant Force",
                        "initialStress": {
                            "value": _float_to_str(test["stress_value"]),
                            "unit": test["stress_unit"],
                        },
                        "testType": "Stress rupture tests where normally only the time to fracture is measured",
                        "endOfTestCriterium": {
                            "endOfTestCriteriumOptions": "Test piece break",
                        },
                        "timeLimit": "Not applicable",
                        "extensionLimit": "Not applicable",
                        "interruptionCourse": "Not applicable",
                    },
                },
                "MaterialHistoryAndCondition": {
                    "materialIdentifier": "ERBO/1 (CMSX-4 type)",
                    "asManufacturedMaterial": {
                        "solidification": "Single crystal",
                        "monocrystalOrientation": orientation,
                        "condition": "Heat treated",
                        "formOfAsManufacturedMaterial": "Cast plate",
                        "geometrySizeAsManufacturedMaterial": "140 mm × 100 mm × 20 mm",
                    },
                    "microstructureNi-BasedSX": {
                        "singleCrystalOrientation": orientation,
                        "singleCrystalOrientationDeterminationMethod": "Laue technique",
                        "orientationDeterminationAccuracy": "< 1°",
                    },
                    "heatTreatment": {
                        "heatTreatmentDescription": (
                            "Solution annealed and precipitation hardened ERBO/1 (CMSX-4 type). "
                            "See Parsa et al., Adv. Eng. Mater. 17 (2015) 216-230."
                        ),
                        "heatTreatmentState": {
                            "heatTreatmentStateOptions": "Other (Please specify in the comment)",
                            "otherHeatTreatmentState": "Solution annealed and precipitation hardened",
                        },
                        "heatTreatmentAnnealingDescription": _HEAT_TREATMENT_ANNEALING,
                        "heatTreatmentAgeingDescription": _HEAT_TREATMENT_AGEING,
                    },
                },
            },
            "PrimaryData": {
                "TestResult": {
                    "valuesRecordedAfterTestEnd": {
                        "creepRuptureTime": {
                            "value": _float_to_str(test["rupture_time_value"]),
                            "unit": test["rupture_time_unit"],
                        },
                        "fracturePosition": "Not applicable",
                    },
                },
            },
            "SecondaryData": {
                "TestResult": {
                    "dataSeries": {
                        "creepCurve": ZENODO_CREEP_CURVE_BASE + "SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx",
                    },
                },
            },
        },
    }

    return doc


# ─── Auto-fill required schema fields ─────────────────────────────────────────

def _fill_required_fields(doc: dict, schema_file: str) -> tuple[dict, int]:
    """Fill missing required schema fields with 'TODO' defaults."""
    sys.path.insert(0, _script_dir)
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "validation_core", os.path.join(_script_dir, "validation_core.py")
        )
        vc = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vc)
    except Exception as exc:
        Logger.warning("Could not load validation_core: %s — skipping auto-fill", exc)
        return doc, 0

    with open(schema_file, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    filled, changes = vc.autofix_required_fields(schema, schema, doc)
    return filled, changes


# ─── Schema validation ─────────────────────────────────────────────────────────

def validate_against_schema(data: dict, schema_file: str) -> list[dict]:
    from jsonschema import Draft201909Validator
    with open(schema_file, "r", encoding="utf-8") as fh:
        schema = json.load(fh)
    errors = []
    for err in Draft201909Validator(schema).iter_errors(data):
        path = "/".join(str(p) for p in err.absolute_path)
        errors.append({"path": path, "message": err.message})
    return sorted(errors, key=lambda e: (e["path"], e["message"]))


# ─── Main ──────────────────────────────────────────────────────────────────────

def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="translate_rub_data.py",
        description="Translate RUB SX-creep Excel to schema v2.1.8 JSON files",
    )
    p.add_argument(
        "excel_file",
        nargs="?",
        default=None,
        help="Path to SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx. "
             "Defaults to Data/RUBDataset/SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx",
    )
    p.add_argument(
        "--download",
        action="store_true",
        help="Download the Excel from Zenodo if it is not present locally.",
    )
    p.add_argument(
        "-o", "--output-dir",
        dest="output_dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Output directory for JSON files (default: Data/RUBDataset_Json/)",
    )
    p.add_argument(
        "--schema",
        dest="schema_file",
        default=DEFAULT_SCHEMA_FILE,
        help="Path to the JSON schema for validation.",
    )
    p.add_argument(
        "--validate",
        action="store_true",
        help="Run schema validation on each output JSON and report errors.",
    )
    p.add_argument(
        "--autofill",
        dest="autofill",
        action="store_true",
        default=False,
        help="Auto-fill missing required schema fields with 'TODO' defaults.",
    )
    return p


def main(argv=None) -> int:
    args = _build_arg_parser().parse_args(argv)

    excel_path = args.excel_file or DEFAULT_EXCEL_PATH

    if args.download and not os.path.isfile(excel_path):
        _download_excel(excel_path)

    if not os.path.isfile(excel_path):
        Logger.error(
            "Excel file not found: %s\n"
            "Run with --download to fetch it from Zenodo, or provide the path explicitly.",
            excel_path,
        )
        return 1

    os.makedirs(args.output_dir, exist_ok=True)

    global_meta, tests = read_rub_excel(excel_path)

    if not tests:
        Logger.error("No test data parsed from the Excel file.")
        return 1

    error_count = 0
    for test in tests:
        doc = translate_rub_test(global_meta, test)

        if args.autofill and os.path.isfile(args.schema_file):
            doc, n_filled = _fill_required_fields(doc, args.schema_file)
            if n_filled:
                Logger.info(
                    "%s: auto-filled %d required field(s) with TODO",
                    _make_test_id(test), n_filled,
                )

        fname = _make_test_id(test) + "_translated.json"
        out_path = os.path.join(args.output_dir, fname)
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=4, ensure_ascii=False)

        if args.validate and os.path.isfile(args.schema_file):
            errs = validate_against_schema(doc, args.schema_file)
            if errs:
                Logger.warning("%s: %d schema error(s)", fname, len(errs))
                for e in errs:
                    Logger.warning("  [%s] %s", e["path"], e["message"])
                error_count += len(errs)

    Logger.info(
        "Done. %d JSON files written to %s", len(tests), args.output_dir
    )
    if args.validate:
        Logger.info("Total schema validation errors: %d", error_count)

    return 0


if __name__ == "__main__":
    sys.exit(main())
