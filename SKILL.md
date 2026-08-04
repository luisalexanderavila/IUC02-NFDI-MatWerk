# IUC02 Project — Copilot SKILL Reference

> NFDI-MatWerk Infrastructure Use Case 02 — Framework for Curation and Distribution of Reference Datasets  
> **Domain:** Creep experiments on Ni-base single-crystal superalloys (CMSX-6), BAM + RUB datasets  
> **Python environment:** conda env `python311` (Python 3.11)  
> **Last updated:** 2026-06-09 — schema v2.1.8, datasets BAMDataset_v20260608 + RUBDataset (41 tests)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Data: LIS Files (BAM)](#3-data-lis-files)
4. [Data Schema](#4-data-schema)
5. [Parsing: LISParser Module](#5-parsing-lisparser-module)
6. [LIS → JSON Conversion (Mapping)](#6-lis--json-conversion-mapping)
7. [RUB Excel → JSON Conversion](#7-rub-excel--json-conversion)
8. [Validation](#8-validation)
9. [Metadata Validation Web App (Flask)](#9-metadata-validation-web-app-flask)
10. [RDF / SHACL Pipeline](#10-rdf--shacl-pipeline)
11. [RDF Visualization Web App (Flask)](#11-rdf-visualization-web-app-flask)
12. [Demonstrator App (Streamlit)](#12-demonstrator-app-streamlit)
13. [Data Download from Zenodo](#13-data-download-from-zenodo)
14. [Batch Processing](#14-batch-processing)
15. [Tests](#15-tests)
16. [Environment & Dependencies](#16-environment--dependencies)
17. [End-to-End Workflow Summary](#17-end-to-end-workflow-summary)

---

## 1. Project Overview

IUC02 captures, structures, and validates metadata of creep experiments on CMSX-6 single-crystal Ni-base superalloys. Two datasets are supported:

- **BAM dataset** (Berlin) — LIS text files, compressive or tensile creep, 12 specimens
- **RUB dataset** (Ruhr-Universität Bochum) — Excel file, tensile creep, 41 tests across [001]/[110]/[111] orientations

Core workflow:

```
BAM:  LIS file  →  LisParseV2  →  flat dict  →  BAM2schema_v2.json  →  JSON experiment document
RUB:  Excel     →  pandas       →  test dict  →  hardcoded mapping   →  JSON experiment document
                                                                               ↓
                                                    validate against JSON Schema v2.1.8
                                                                               ↓
                                                    convert to RDF Turtle → SHACL validation
```

A Flask-based local web app (`metadata_validation_web_app.py`) drives the middle of this pipeline interactively. A Streamlit demonstrator app shows the end-to-end workflow for stakeholders.

---

## 2. Repository Layout

```
iuc02/
├── Data Schema/                      # JSON Schema files (all versions)
│   ├── 2026-06_Data-Schema_Creep_v2.1.8.json   ← CURRENT schema
│   ├── 2026-06_Data-Schema_Creep_v2.1.7.json
│   ├── 2026-06_Data-Schema_Creep_v2.1.6.json
│   ├── 2026-06_Schema-Changes_v2.1.5-to-v2.1.6.md
│   └── IntendedSchemaStructure.md
├── Demonstrator_App/                 # Streamlit app
│   ├── IUC02_Demonstrator.py         # entry point
│   └── pages/
│       ├── Data_Generation.py
│       ├── Data_Validation.py
│       └── About_Us.py
├── Parsing/
│   ├── bin/                          # CLI scripts and web apps
│   │   ├── metadata_validation_web_app.py   ← main validation web app
│   │   ├── metadata_validation_web_app.bat  ← launcher (Windows)
│   │   ├── translate_bam_data_v2.py         ← BAM LIS → JSON converter (schema v2.1.8)
│   │   ├── translate_rub_data.py            ← RUB Excel → JSON converter (schema v2.1.8)
│   │   ├── validation_core.py               ← shared validation logic
│   │   ├── shacl_validation_core.py
│   │   ├── visualization_core.py
│   │   ├── visualization_web_app.py         ← RDF viz web app
│   │   ├── visualization_web_app_python311.bat
│   │   ├── get_data_from_zenodo.py
│   │   ├── run_batch_validation.py
│   │   ├── complete_json.py
│   │   ├── validate_json.py
│   │   ├── create_visualization.py
│   │   ├── bam2shacl.py
│   │   ├── json_to_shacl.py
│   │   └── run_all_checks.py / run_all_checks.bat
│   ├── Data/
│   │   ├── BAMDataset_v20260608/     ← CURRENT versioned LIS dataset (12 MD-TR files)
│   │   │   ├── Vh5205_C-<T>-MD-TR.lis   ← main metadata files (UTF-8 no BOM, CRLF)
│   │   │   ├── Vh5205_C-<T>-Creep.LIS
│   │   │   ├── Vh5205_C-<T>-Loading.LIS
│   │   │   ├── Vh5205_Complementary_*.LIS
│   │   │   └── _batch_translated/    ← pre-generated JSON outputs
│   │   ├── BAMDataset_Json/          ← BAM active JSON output (regenerated from v20260608)
│   │   ├── BAMDataset_v052026/       ← previous BAM dataset version (keep for reference)
│   │   ├── BAMDataset_v20260608.zip  ← zip archive for distribution
│   │   ├── RUBDataset/               ← RUB source data directory
│   │   │   ├── SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx  ← source Excel (Zenodo 7663974)
│   │   │   └── CLAUDE.md             ← Claude Code reference for RUB pipeline
│   │   └── RUBDataset_Json/          ← RUB JSON output (41 tests: 19+11+11)
│   ├── dependencies/
│   │   ├── LISParser/LISParser/
│   │   │   ├── LisParseV2.py         ← v2 parser (current)
│   │   │   └── LisParse.py           ← v1 legacy parser
│   │   └── Mappingsreader/mappingsreader/
│   │       └── mapreader.py
│   ├── Metadata/Mappings/
│   │   ├── BAM2schema_v2.json        ← mapping doc for v2 LIS → schema (UTF-8 BOM)
│   │   └── BAM2schema.json           ← mapping doc for v1 LIS
│   ├── test/                         # pytest tests
│   ├── shacl_validation/             # example TTL files
│   ├── Notebooks/
│   ├── requirements.txt
│   └── environment.yaml
├── Data Validation/
├── Ontology Development/
└── README.md
```

---

## 3. Data: LIS Files

### Format

LIS files are tab-separated text files (encoding: `latin1`) with two sections:

**Metadata section** — one metadata field per row:

```
CATEGORIZATION                              ENTRY               ...  REQUIREMENT  INFORMATION                 INFORMATION COMMON TO ALL (*)
Metadata --> Test info --> Test job details  Date of test start  ...  Mandatory    2023-02-08 09:06:15         *
```

| Column index | Header                         | Content                                    |
|--------------|--------------------------------|--------------------------------------------|
| 0            | CATEGORIZATION                 | Hierarchical path: `A --> B --> C`         |
| 1            | ENTRY                          | Field label                                |
| 2            | ENTRY - ADDITIONAL INFORMATION | Free-text description                      |
| 3            | SYMBOL                         | Physical symbol (e.g. `T`, `Ro`)           |
| 4            | UNIT                           | Physical unit (e.g. `°C`, `MPa`)           |
| 5            | REQUIREMENT                    | `Mandatory` or `Optional`                  |
| 6            | INFORMATION                    | **The actual value**                       |
| 7            | INFORMATION COMMON TO ALL (*)  | `*` if field is identical across specimens |

**Data section** — starts with `[data]` marker, followed by:
- Row 1: column titles
- Row 2: symbols
- Row 3: units
- Rows 4+: numeric time-series values (comma as decimal separator)

### File naming conventions

| Pattern                          | Content                              |
|----------------------------------|--------------------------------------|
| `Vh5205_C-<T>-MD-TR.lis`        | Main metadata (parse target)         |
| `Vh5205_C-<T>-Creep.LIS`        | Creep time-series data               |
| `Vh5205_C-<T>-Loading.LIS`      | Loading data                         |
| `Vh5205_Complementary_*.LIS`     | Shared complementary metadata (heat treatment, chemical composition, roughness, etc.) |

`<T>` is the specimen/test number (e.g. `78`, `80`, `81`, …`99`).

### Version detection

A **v2** LIS file starts with the header line beginning with `CATEGORIZATION`. Files without this header are treated as the legacy **v1** format.

### Multi-line values

Some field values span multiple continuation lines (lines that lack both the `-->` path separator and a tab-delimited column structure). The parser collects and joins them with `\n`.

---

## 4. Data Schema

### Current version: `2026-06_Data-Schema_Creep_v2.1.8.json`

**JSON Schema Draft 2019-09.** Located at `Data Schema/`.

#### Top-level structure

```
MeasurementData (required)
 ├── AdditionalMetadata (required)
 │     ├── TestInfo
 │     │     ├── testJobDetails          (required: dateOfTestStart, dateOfTestEnd, testID)
 │     │     └── testParameters          (required: testStandardApplied, testStandard,
 │     │                                  specifiedTemperature, typeOfLoading, loadControlType,
 │     │                                  initialStress, testType, endOfTestCriterium,
 │     │                                  timeLimit, extensionLimit, interruptionCourse, preload)
 │     ├── MaterialHistoryAndCondition
 │     │     ├── asManufacturedMaterial
 │     │     ├── asTestedMaterial
 │     │     ├── heatTreatment
 │     │     ├── microstructure          (array)
 │     │     ├── microstructureNi-BasedSX
 │     │     ├── chemicalComposition     (array)
 │     │     ├── ndtResults
 │     │     └── mechanicalTestResults
 │     ├── TestPiece
 │     │     ├── testPieceTypeI          (enum + allOf conditional)
 │     │     ├── testPieceTypeIStandard  (conditional: when typeI = "Specimen according to standard")
 │     │     └── ...
 │     ├── MeasuringAndTestEquipment
 │     │     ├── testMachine
 │     │     │     ├── testFrameAndSpecimenAlignment
 │     │     │     ├── testFrameAndSpecimenAlignmentDescription
 │     │     │     ├── testFrameAndSpecimenAlignmentDate  (optional string, v2.1.7)
 │     │     │     └── ...
 │     │     ├── loadSensor
 │     │     ├── temperatureSensor
 │     │     ├── extensometerSystem
 │     │     └── elongationValuesAndCrossSectionalDimensions
 │     └── DataProcessingProcedures
 ├── PrimaryData (required)
 │     └── TestResult
 └── SecondaryData (required)
       └── TestResult
```

#### Key naming conventions

Top-level section keys are **PascalCase**: `AdditionalMetadata`, `TestInfo`, `MaterialHistoryAndCondition`, `TestPiece`, `MeasuringAndTestEquipment`, `DataProcessingProcedures`, `PrimaryData`, `SecondaryData`, `TestResult`.

Leaf-level field keys are **camelCase** (e.g., `dateOfTestStart`, `specifiedTemperature`).

#### Reusable `$defs`

| Def name                                 | Description                                           |
|------------------------------------------|-------------------------------------------------------|
| `ComplexValue`                           | `{value: string, unit: string}`                       |
| `ChemicalCompositionElementsList`        | Array of `{element, value, unit, measurementMethod}`  |
| `ChemicalCompositionNominalElementsList` | Array of `{element, value, unit}`                     |
| `ChemicalCompositionExternalFile`        | `{externalFileLink: string}`                          |

#### Dropdown fields — "Other" pattern

When a field has enum options AND an "Other (Please specify in the comment)" option, it uses the `*Options` / `other*` sibling pattern:

```json
"testStandard": {
  "properties": {
    "testStandardOptions": { "type": "string", "enum": ["ISO 204", "ASTM E139", "Other (Please specify in the comment)"] },
    "otherTestStandard": { "type": "string" }
  }
}
```

When the LIS value doesn't match any option, B6 sets `testStandardOptions = "Other (Please specify...)"` and writes the raw LIS value to `otherTestStandard`.

Fields **without** "Other" option require an exact match — mismatch is logged as ERROR.

#### Schema changelog

**v2.1.6** (from v2.1.5):
- `interruptionCourse`: added `"Not applicable"` to enum
- `fracturePosition`: added `"Not applicable"` to enum
- `TestPiece.allOf`: conditional — when `testPieceTypeI = "Specimen according to standard"`, `testPieceTypeIStandard` becomes available

**v2.1.7** (from v2.1.6):
- `testMachine`: added optional `testFrameAndSpecimenAlignmentDate` string property after `testFrameAndSpecimenAlignmentDescription`

**v2.1.8** (from v2.1.7):
- `loadSensorCalibration`: changed from plain string to enum (`Yes`/`No`); added sibling `loadSensorCalibrationDescription` string
- `temperatureMeasuringSystem.dataAcquisition.calibrationStandard`: added description hint `E.g., EURAMET/cg-11/v.01`
- `SecondaryData.TestResult.dataSeries.creepCurve`: new mandatory string field (link to Zenodo creep file); `dataSeries` object now has `"required": ["creepCurve"]`
- `castingTemperature` / `castingAtmosphere`: changed from array-of-ComplexValue to single ComplexValue

---

## 5. Parsing: LISParser Module

**Location:** `Parsing/dependencies/LISParser/LISParser/`

### `LisParseV2.py` — `ParserV2` class (current)

```python
from LISParser.LisParseV2 import ParserV2

parser = ParserV2("path/to/Vh5205_C-78-MD-TR.lis")
result = parser.parse_lis()
```

**Output dict structure:**
```python
{
    "filename": "Vh5205_C-78-MD-TR.lis",
    "lis_version": "v2",
    "schema_version": "2025-12",
    "metadata": {
        "test info": {
            "test job details": {
                "date of test start": {
                    "value": "2023-02-08 09:06:15",
                    "unit": "", "symbol": "",
                    "requirement": "Mandatory", "common": True
                }
            }
        },
        ...
    },
    "primary_data": { ... },
    "secondary_data": { ... },
    "data": {
        "Elapsed time from end of loading": {"unit": "h", "values": [0.0, 0.5, ...]},
        ...
    }
}
```

All path segments and entry labels are **normalized to lowercase** (`casefold()`).

**`get_flat_metadata()`** returns a flat dict keyed by `section.subsection.field_name` (all lowercase), used by the mapping layer:
```python
flat = parser.get_flat_metadata()
# flat["metadata.test info.test job details.date of test start"]
# → {"value": "2023-02-08", "unit": "", ...}
```

### `LisParse.py` — legacy v1 parser

Used automatically when the file does not have the `CATEGORIZATION` header. Returns a similar dict but with `lis_version: "v1"`.

---

## 6. LIS → JSON Conversion (Mapping)

**Script:** `Parsing/bin/translate_bam_data_v2.py`  
**Mapping document:** `Parsing/Metadata/Mappings/BAM2schema_v2.json` (UTF-8 **with BOM** — open with `encoding="utf-8-sig"`)  
**Default schema:** `2026-06_Data-Schema_Creep_v2.1.8.json`

### Running

```bash
# Single file (from Parsing/ directory, python311 env active):
python bin/translate_bam_data_v2.py Data/BAMDataset_v20260608/Vh5205_C-78-MD-TR.lis \
  -o Data/BAMDataset_Json/Vh5205_C-78-MD-TR_translated.json

# Batch all 12 MD-TR files (PowerShell):
$py = "C:\Users\maria\anaconda3\envs\python311\python.exe"
foreach ($f in Get-ChildItem "Data\BAMDataset_v20260608\*-MD-TR.lis") {
    $out = "Data\BAMDataset_Json\$($f.BaseName)_translated.json"
    & $py bin\translate_bam_data_v2.py $f.FullName -o $out
}
```

### Mapping document format (`BAM2schema_v2.json`)

```json
{
  "mappedMeasurementData": {
    "metadata.test info.test job details.date of test start":
        "MeasurementData.AdditionalMetadata.TestInfo.testJobDetails.dateOfTestStart",
    ...
  }
}
```

- **Keys** — flat, dot-separated, all-lowercase LIS path (`section.path.field`)
- **Values** — dot-separated target schema path (`MeasurementData.AdditionalMetadata.…`)
- Note: `suffix_map` keys in the translator use the PascalCase schema path suffix exactly as it appears in the schema (e.g., `TestPiece.testPieceTypeI`, not `testPiece.testPieceTypeI`)

### Key logic in `translate_v2()`

1. Flatten parsed LIS dict to `flat_records` (case-insensitive key lookup)
2. For each mapping entry, look up the record and extract `.value`
3. Normalize value via `_normalize_value_for_schema_path()` using `suffix_map` (exact lowercase match only — no `startswith` fallback)
4. Apply **B6 Other-detection** (`_try_other_detection`) on every enum-constrained path:
   - Exact case-sensitive comparison (`stripped == opt`)
   - `*Options` fields with "Other (Please specify...)" in enum → write `other*` sibling on mismatch
   - All enum fields without "Other" option → log `ERROR` on mismatch
   - Array indices stripped before enum lookup: `re.sub(r'\.(\d+)\.', '.', schema_path)`
5. Handle chemical composition external references (`See file …`)
6. Handle leverageRatio extraction from test machine type values
7. Post-process: `_fix_int_keys()` converts integer-keyed dicts to Python lists

### Enum handling rules (important)

| Situation | Behaviour |
|-----------|-----------|
| LIS value exactly matches enum option (case-sensitive) | Written as-is |
| LIS value doesn't match; field has "Other (Please specify...)" option | `*Options = "Other..."`, `other* = raw LIS value` |
| LIS value doesn't match; field has NO "Other" option | `ERROR` logged; value written as-is |
| `suffix_map` has a lowercase alias for the path | Normalized before B6 check |

### Output: JSON experiment document

Conforms to schema structure starting from `MeasurementData`. Saved to `Parsing/Data/BAMDataset_Json/`.

---

## 7. RUB Excel → JSON Conversion

**Script:** `Parsing/bin/translate_rub_data.py`  
**Source:** `SX-CREEP-DATA_LWW-RUB_JAN2023.xlsx` (Zenodo record `7663974`)  
**Output:** `Parsing/Data/RUBDataset_Json/RUB_{orientation}_{temp}C_{stress}MPa_translated.json`  
**Reference:** `Parsing/Data/RUBDataset/CLAUDE.md`

### Running

```powershell
$py = "C:\Users\maria\anaconda3\envs\python311\python.exe"
cd "C:\Users\maria\Desktop\IUC02\iuc02\Parsing"

# All 41 tests (autofill off by default — real values preserved):
& $py bin\translate_rub_data.py

# Download Excel from Zenodo first if missing:
& $py bin\translate_rub_data.py --download

# With schema validation output:
& $py bin\translate_rub_data.py --validate

# With auto-fill of missing required fields (adds TODO placeholders):
& $py bin\translate_rub_data.py --autofill
```

### Excel structure

| Sheet | Content |
|-------|---------|
| `Overview` | Global metadata: title, licence, heat treatment (row 18), publication (row 21), preparation (row 24), experiments (rows 27–28) |
| ` 001-direction` | 19 test tables — tensile creep for [001] crystal orientation |
| `110-direction` | 11 test tables — tensile creep for [110] crystal orientation |
| `111-direction` | 11 test tables — tensile creep for [111] crystal orientation |

Each orientation sheet: 3 columns per test (`time_s | strain | separator`).  
- **Row 6:** `"temp/stress"` header — e.g. `"720/800"` → 720 °C / 800 MPa  
- **Row 7:** metadata string with rupture time — e.g. `"Rupture time: 971 h"`  
- **Rows 8+:** numeric time (seconds) and strain (dimensionless, absolute)

### Schema mapping

| RUB Excel field | Schema path |
|----------------|-------------|
| Temperature (row 6 of each table) | `AdditionalMetadata.TestInfo.testParameters.specifiedTemperature` (ComplexValue, unit °C) |
| Stress (row 6 of each table) | `AdditionalMetadata.TestInfo.testParameters.initialStress` (ComplexValue, unit MPa) |
| Crystal orientation (sheet name) | `...MaterialHistoryAndCondition.asManufacturedMaterial.monocrystalOrientation` |
| Heat treatment (Overview row 18) | `...MaterialHistoryAndCondition.heatTreatment.heatTreatmentDescription` |
| Rupture time (row 7 of each table) | `PrimaryData.TestResult.valuesRecordedAfterTestEnd.creepRuptureTime` (ComplexValue, unit h) |
| Zenodo Excel URL | `SecondaryData.TestResult.dataSeries.creepCurve` (points to source .xlsx) |

### Auto-fill behavior

`--autofill` (opt-in) calls `autofix_required_fields()` from `validation_core.py` to fill missing schema-required fields with "TODO".  
**Important:** by default this is disabled because the function has a bug — it replaces existing non-dict leaf values with `{}` when the schema node has `properties: {}`. Do not enable until that bug is fixed in `validation_core.py`.

### Known limitations

- No specimen geometry (parallel/gauge length, diameter)
- No equipment details (test machine, load sensor, extensometer)
- No chemical composition data
- Strain is absolute (dimensionless), not percentage
- `typeOfLoading` is hardcoded to `"Constant Stress"` — verify against source

---

## 8. Validation

**Module:** `Parsing/bin/validation_core.py`

### Functions

| Function | Description |
|---|---|
| `validate_required_keywords(schema, doc)` | Walk schema `required` arrays; check all required paths are present and non-empty. Returns `(req_paths, warnings, schema_target, data_target)`. |
| `run_jsonschema_validation(schema, data)` | Full Draft 2019-09 validation via `jsonschema`. Returns list of `{data_path, message, schema_path}` dicts. |
| `autofix_required_fields(schema, schema_node, data_node)` | Recursively fill missing required fields with inferred defaults. |
| `autofix_schema_errors(schema, data)` | Multi-pass auto-fix using jsonschema error feedback (handles `required`, `type`, `enum`, `minItems`). |
| `infer_default_value(schema_root, schema_node)` | Infer a placeholder value from schema node type/enum. Returns `"TODO"` for plain strings. |
| `normalize_experiment_data(schema, doc)` | Handles legacy wrapper keys (`mappedMeasurementData`, old camelCase top-level keys). |

### Document normalization

The validator accepts JSON experiment documents in several forms:
- Directly starting with `MeasurementData`
- Wrapped in `{"mappedMeasurementData": {"MeasurementData": ...}}`
- Using old camelCase top-level keys (`additionalMetadata`, `primaryData`, `secondaryData`) — automatically wrapped

### CLI: `complete_json.py`

Interactive or non-interactive tool to fill in missing required fields:

```bash
python bin/complete_json.py \
  --file path/to/experiment.json \
  --schema "../Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json"
```

---

## 9. Metadata Validation Web App (Flask)

**Script:** `Parsing/bin/metadata_validation_web_app.py`  
**Launcher:** `Parsing/bin/metadata_validation_web_app.bat`  
**Default port:** `8503`  
**Default schema:** `Data Schema/2026-06_Data-Schema_Creep_v2.1.8.json`  
**Default LIS folder:** `Data/BAMDataset_v20260608`

### Starting

```bash
# From Parsing/ directory, python311 env active:
python bin/metadata_validation_web_app.py

# Custom port/schema:
python bin/metadata_validation_web_app.py --port 9000 \
  --schema "../Data Schema/2026-06_Data-Schema_Creep_v2.1.7.json"
```

### Features

| Feature | Description |
|---|---|
| **Schema selector** | Dropdown with `name="schema_path"`, posts value directly on change (same pattern as other dropdowns) |
| **JSON file picker** | Lists `.json` files under `Data/BAMDataset_Json/` |
| **LIS file picker** | Lists `*-MD-TR.lis` files under `Data/BAMDataset_v20260608/` and discoverable folders |
| **Convert LIS → JSON** | Invokes `translate_bam_data_v2.py`; saves to `BAMDataset_Json/` |
| **Load & validate** | Loads JSON, runs required-path check + full JSON Schema validation |
| **Tree view** | Renders JSON against schema as an expandable HTML tree |
| **Validation highlighting** | Missing required fields in **red**, present required fields in **green** |
| **Auto-fix** | Triggers `autofix_schema_errors()` and saves fixed JSON |
| **SHACL validation** | Runs `shacl_validation_core` on TTL graphs |

### Dropdown rendering rule for `*Options` / Other fields

When rendering a `*Options` field that starts with `"Other"`, the display value is taken from the `other*` sibling (the actual LIS value), not from the raw `"Other (Please specify...)"` string. This is applied in `_build_leaf_html` (~line 640).

### `_resolve_for_render()` — allOf merge (important)

When a schema node has both local `properties` and an `allOf` array:
- Merged properties are **seeded from the node's own `properties`** first
- Each allOf member's `properties` are added (without overwriting)
- `then.properties` from `if/then` conditionals are also included (for conditional fields like `testPieceTypeIStandard`)

This prevents the entire object from being serialized as a raw JSON string instead of a tree.

---

## 10. RDF / SHACL Pipeline

**Scripts:** `Parsing/bin/bam2shacl.py`, `json_to_shacl.py`, `json_to_shacl_2.py`, `shacl_validation_core.py`, `validate_rdf_shacl.py`  
**Example files:** `Parsing/shacl_validation/rdfGraph_smallExample.ttl`, `shaclShape_smallExample.ttl`

### Workflow

1. **JSON → RDF Turtle** — `bam2shacl.py` / `json_to_shacl.py` convert the JSON experiment document to a knowledge-graph Turtle file
2. **SHACL validation** — `shacl_validation_core.run_shacl_validation(data_ttl, shapes_ttl)` uses `pyshacl` + `rdflib`
3. **Output** — Returns `{conforms: bool, results: [...], report_text: str}`

### SHACL shape generation

`Parsing/dependencies/creep_shacl_maker/` contains tools to derive SHACL shapes from the JSON Schema.

---

## 11. RDF Visualization Web App (Flask)

**Script:** `Parsing/bin/visualization_web_app.py`  
**Launcher:** `Parsing/bin/visualization_web_app_python311.bat`  
**Default port:** `8502`

Accepts a Turtle (`.ttl`) file path, generates an interactive HTML network graph using `pyvis` (hierarchical left-to-right layout), and displays it in an iframe.

```bash
python bin/visualization_web_app.py \
  --input shacl_validation/rdfGraph_smallExample.ttl
```

Static generation via CLI:
```bash
python bin/create_visualization.py
# → Parsing/Notebooks/rdf_graph_viewer.html
```

---

## 12. Demonstrator App (Streamlit)

**Location:** `Demonstrator_App/`  
**Entry point:** `Demonstrator_App/IUC02_Demonstrator.py`  
**Deployed at:** https://iuc-02-demonstrator.vercel.app

### Pages

| Page | File | Description |
|---|---|---|
| Home / Summary | `page_summary.py` | Overview and project info |
| Data Generation | `pages/Data_Generation.py` | Workflow diagram; file viewer/editor with download |
| Data Validation | `pages/Data_Validation.py` | Upload RDF + SHACL shapes; run pyshacl; show report |
| About Us | `pages/About_Us.py` | Project/team information |

### Running locally

```bash
cd Demonstrator_App
conda activate python311
streamlit run IUC02_Demonstrator.py
```

---

## 13. Data Download from Zenodo

**Script:** `Parsing/bin/get_data_from_zenodo.py`

```bash
# From Parsing/ directory, python311 env active:
python bin/get_data_from_zenodo.py
# Default: downloads Zenodo record 18933930 → Data/BAMDataset/

# Legacy dataset:
python bin/get_data_from_zenodo.py \
  --zenodo-id 13937987 --output-dir Data/BAMDataset_legacy
```

Downloads the full `.zip` archive and extracts it in-place.

**Zenodo records:**

| Record ID | Version |
|-----------|---------|
| `20132712` | Current/latest dataset |
| `13937987` | Legacy v1 dataset |

---

## 14. Batch Processing

**Script:** `Parsing/bin/run_batch_validation.py`

Processes all `*-MD-TR.lis` files in `Data/BAMDataset_v032026/`:
1. Calls `translate_bam_data_v2.py` on each file → saves JSON to `_batch_translated/`
2. Calls `validate_json.py` on each resulting JSON against the current schema
3. Prints a summary of translation and validation results

```bash
cd Parsing
conda activate python311
python bin/run_batch_validation.py
```

Pre-generated outputs already exist in `Data/BAMDataset_v032026/_batch_translated/`.

---

## 15. Tests

**Location:** `Parsing/test/`  
**Framework:** `pytest`

| Test file | Coverage |
|---|---|
| `test_lis_parse.py` | LIS file parsing (v1 and v2) |
| `test_new_features.py` | New v2 parser features and edge cases |
| `test_read_mapping.py` | Mapping document loading and lookup |
| `test_translate_bam_data_v2.py` | End-to-end LIS → JSON translation |

```bash
cd Parsing
conda activate python311
pytest test/ -q
```

Full setup + test + visualization:
```bash
python bin/run_all_checks.py
# Windows: bin\run_all_checks.bat
```

---

## 16. Environment & Dependencies

**Conda environment:** `python311` (Python 3.11)

Key packages:

| Package | Used for |
|---|---|
| `flask` | Metadata validation web app, visualization web app |
| `markupsafe` | HTML escaping in Flask templates |
| `jsonschema` | JSON Schema Draft 2019-09 validation (`Draft201909Validator`) |
| `rdflib` | RDF graph parsing and serialization |
| `pyshacl` | SHACL constraint validation |
| `pyvis` | Interactive RDF graph visualization (HTML/JS) |
| `streamlit` | Demonstrator app |
| `requests` | Zenodo download |
| `pandas`, `numpy` | Data processing notebooks |
| `pytest` | Test suite |

**Installing dependencies (Parsing scripts):**
```bash
cd Parsing
conda activate python311
pip install -r requirements.txt
```

**Local dependency packages** (injected into `sys.path` by scripts):
- `LISParser` — `Parsing/dependencies/LISParser/`
- `Mappingsreader` — `Parsing/dependencies/Mappingsreader/`

---

## 17. End-to-End Workflow Summary

```
─── BAM pipeline ─────────────────────────────────────────────────────────────

Step 1 — Download BAM data (optional)
  python Parsing/bin/get_data_from_zenodo.py
  → Parsing/Data/BAMDataset/

Step 2 — Parse a LIS file
  ParserV2("Vh5205_C-78-MD-TR.lis").parse_lis()
  → hierarchical dict (metadata / primary_data / secondary_data / data)

Step 3 — Translate to JSON experiment document
  python Parsing/bin/translate_bam_data_v2.py \
    Data/BAMDataset_v20260608/Vh5205_C-78-MD-TR.lis \
    -o Data/BAMDataset_Json/Vh5205_C-78-MD-TR_translated.json
  → conforms to Data Schema/2026-06_Data-Schema_Creep_v2.1.8.json

Step 4 — Batch translate all 12 MD-TR files (PowerShell)
  $py = "C:\Users\maria\anaconda3\envs\python311\python.exe"
  foreach ($f in Get-ChildItem "Data\BAMDataset_v20260608\*-MD-TR.lis") {
      $out = "Data\BAMDataset_Json\$($f.BaseName)_translated.json"
      & $py bin\translate_bam_data_v2.py $f.FullName -o $out
  }

─── RUB pipeline ─────────────────────────────────────────────────────────────

Step 1 — Translate RUB Excel to 41 JSON files
  $py = "C:\Users\maria\anaconda3\envs\python311\python.exe"
  cd "C:\Users\maria\Desktop\IUC02\iuc02\Parsing"
  & $py bin\translate_rub_data.py
  → Data/RUBDataset_Json/RUB_*_translated.json (41 files)

  # First-time download from Zenodo:
  & $py bin\translate_rub_data.py --download

─── Shared steps ─────────────────────────────────────────────────────────────

Step 5 — Validate JSON
  validation_core.validate_required_keywords(schema, doc)
  → missing-field warnings list
  validation_core.run_jsonschema_validation(schema, data)
  → full schema errors list

Step 6 — Interactive validation in web app
  python Parsing/bin/metadata_validation_web_app.py
  → open http://127.0.0.1:8503
  - Pick LIS file → Convert → inspect tree → highlight missing fields → auto-fix

Step 7 — Convert to RDF and validate with SHACL
  python Parsing/bin/bam2shacl.py ...
  python Parsing/bin/validate_rdf_shacl.py ...

Step 8 — Visualize RDF graph
  python Parsing/bin/visualization_web_app.py
  → open http://127.0.0.1:8502
```

### Current dataset specimens (BAMDataset_v20260608)

Tests: **C-78, C-80, C-81, C-82, C-85, C-89, C-91, C-94, C-95, C-97, C-98, C-99**  
Material: CMSX-6 single-crystal Ni-base superalloy  
Temperatures: ~980 °C, stress levels: ~200–300 MPa  
DOI: https://doi.org/10.1016/j.dib.2025.112436

### LIS file encoding and format notes

- **Encoding:** UTF-8 without BOM
- **Line endings:** CRLF (`\r\n`)
- **Parser opens with:** `encoding="utf-8"` — do NOT write with `utf-8-sig` (BOM breaks header detection)
- When modifying LIS files programmatically, read as binary (`rb`), split on `b'\r\n'`, write back as binary (`wb`)

### Known field corrections applied in BAMDataset_v20260608

| Field | Change | Reason |
|-------|--------|--------|
| `Test piece type I` | Value changed from `"Specimen according to DIN EN ISO 204:2019-4"` to `"Specimen according to standard"` | Versioned reference extracted to separate field |
| `Test piece type I standard` | New field added with `"DIN EN ISO 204:2019-4"` | Separates type from standard reference |
| `Test frame and specimen alignment` | Truncated at `Yes`/`No` | Date extracted to separate field |
| `Test frame and specimen alignment - Date` | New field with `"18.07.2011"`, placed after `-description` line | Date now in dedicated field |
