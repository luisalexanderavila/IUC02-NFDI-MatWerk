# IUC02 Project — Copilot SKILL Reference

> NFDI-MatWerk Infrastructure Use Case 02 — Framework for Curation and Distribution of Reference Datasets  
> **Domain:** Creep experiments on Ni-base single-crystal superalloys (CMSX-6), BAM dataset  
> **Python environment:** conda env `python311` (Python 3.11)

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Repository Layout](#2-repository-layout)
3. [Data: LIS Files](#3-data-lis-files)
4. [Data Schema](#4-data-schema)
5. [Parsing: LISParser Module](#5-parsing-lisparser-module)
6. [LIS → JSON Conversion (Mapping)](#6-lis--json-conversion-mapping)
7. [Validation](#7-validation)
8. [Metadata Validation Web App (Flask)](#8-metadata-validation-web-app-flask)
9. [RDF / SHACL Pipeline](#9-rdf--shacl-pipeline)
10. [RDF Visualization Web App (Flask)](#10-rdf-visualization-web-app-flask)
11. [Demonstrator App (Streamlit)](#11-demonstrator-app-streamlit)
12. [Data Download from Zenodo](#12-data-download-from-zenodo)
13. [Batch Processing](#13-batch-processing)
14. [Tests](#14-tests)
15. [Environment & Dependencies](#15-environment--dependencies)
16. [End-to-End Workflow Summary](#16-end-to-end-workflow-summary)

---

## 1. Project Overview

IUC02 captures, structures, and validates metadata of creep experiments performed at BAM. The core workflow is:

```
LIS file  →  parse  →  flat dict  →  map  →  JSON experiment document
                                                     ↓
                              validate against JSON Schema (v2.1.2)
                                                     ↓
                              convert to RDF Turtle → SHACL validation
```

A Flask-based local web app (`metadata_validation_web_app.py`) drives the middle of this pipeline interactively. A Streamlit demonstrator app shows the end-to-end workflow for stakeholders.

---

## 2. Repository Layout

```
iuc02/
├── Data Schema/                      # JSON Schema files (all versions)
│   ├── 2026-04_Data-Schema_Creep_v2.1.2.json   ← CURRENT schema
│   ├── 2026-04_Schema-Changes_v2.1-to-v2.1.2.md
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
│   │   ├── translate_bam_data_v2.py         ← LIS → JSON converter
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
│   │   ├── BAMDataset_v032026/       ← v2 LIS dataset (current)
│   │   │   ├── Vh5205_C-<T>-MD-TR.lis   ← main metadata files
│   │   │   ├── Vh5205_C-<T>-Creep.LIS
│   │   │   ├── Vh5205_C-<T>-Loading.LIS
│   │   │   ├── Vh5205_Complementary_*.LIS
│   │   │   └── _batch_translated/    ← pre-generated JSON outputs
│   │   ├── BAMDataset/               ← downloaded from Zenodo (v1 legacy)
│   │   └── BAMDataset_Json/          ← JSON outputs for v1
│   ├── dependencies/
│   │   ├── LISParser/LISParser/
│   │   │   ├── LisParseV2.py         ← v2 parser (current)
│   │   │   └── LisParse.py           ← v1 legacy parser
│   │   └── Mappingsreader/mappingsreader/
│   │       └── mapreader.py
│   ├── Metadata/Mappings/
│   │   ├── BAM2schema_v2.json        ← mapping doc for v2 LIS → schema
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

### Current version: `2026-04_Data-Schema_Creep_v2.1.2.json`

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
 │     ├── MeasuringAndTestEquipment
 │     │     ├── testMachine
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

#### Key naming conventions (v2.1.2)

Top-level section keys are **PascalCase**: `AdditionalMetadata`, `TestInfo`, `MaterialHistoryAndCondition`, `TestPiece`, `MeasuringAndTestEquipment`, `DataProcessingProcedures`, `PrimaryData`, `SecondaryData`, `TestResult`.

Leaf-level field keys are **camelCase** (e.g., `dateOfTestStart`, `specifiedTemperature`).

#### Reusable `$defs`

| Def name                                 | Description                                           |
|------------------------------------------|-------------------------------------------------------|
| `ComplexValue`                           | `{value: string, unit: string}`                       |
| `ChemicalCompositionElementsList`        | Array of `{element, value, unit, measurementMethod}`  |
| `ChemicalCompositionNominalElementsList` | Array of `{element, value, unit}`                     |
| `ChemicalCompositionExternalFile`        | `{externalFileLink: string}`                          |

#### Schema changelog (v2.1 → v2.1.2)

- `primaryData`/`secondaryData` moved **inside** `MeasurementData`
- `testPiece`, `measuringAndTestEquipment`, `dataProcessingProcedures` moved **inside** `AdditionalMetadata`
- `microstructureNi-BasedSX`, `chemicalComposition`, `ndtResults`, `mechanicalTestResults` moved **inside** `MaterialHistoryAndCondition`
- All top-level section keys renamed from camelCase to **PascalCase**
- `MeasurementData.required` updated to use PascalCase keys

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
**Mapping document:** `Parsing/Metadata/Mappings/BAM2schema_v2.json`

### Running

```bash
# From Parsing/ directory, with python311 conda env active:
python bin/translate_bam_data_v2.py Data/BAMDataset_v032026/Vh5205_C-78-MD-TR.lis

# With explicit output path and schema validation:
python bin/translate_bam_data_v2.py Data/BAMDataset_v032026/Vh5205_C-78-MD-TR.lis \
  --output Data/BAMDataset_v032026/_batch_translated/Vh5205_C-78-MD-TR_schema_v2.json \
  --validate-schema "../Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json"
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

### Key logic in `translate_v2()`

1. Flatten parsed LIS dict to `flat_records` (case-insensitive key lookup)
2. For each mapping entry, look up the record and extract `.value`
3. Normalize value via `_normalize_value_for_schema_path()` for known enum fields  
   (e.g. `"constant force"` → `"Constant Force"`, `"single crystal"` → `"Single crystal"`)
4. Handle **chemical composition external references**: if the value starts with `"See file"`, parse the referenced complementary LIS file and inline the element-by-element data
5. Set value in the nested output dict using `_set_nested_safe()`
6. Post-process: `_fix_int_keys()` converts integer-keyed dicts to Python lists

### Output: JSON experiment document

Conforms to schema structure starting from `MeasurementData`. Pre-generated examples are in `Parsing/Data/BAMDataset_v032026/_batch_translated/`.

---

## 7. Validation

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

## 8. Metadata Validation Web App (Flask)

**Script:** `Parsing/bin/metadata_validation_web_app.py`  
**Launcher:** `Parsing/bin/metadata_validation_web_app.bat`  
**Default port:** `8503`  
**Default schema:** `Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json`

### Starting

```bash
# From Parsing/ directory, python311 env active:
python bin/metadata_validation_web_app.py

# Custom port/schema:
python bin/metadata_validation_web_app.py --port 9000 \
  --schema "../Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json"
```

### Features

| Feature | Description |
|---|---|
| **Schema selector** | Dropdown lists all JSON Schema files found in the `Data Schema/` folder |
| **JSON file picker** | Lists `.json` files under `Data/BAMDataset_Json/` |
| **LIS file picker** | Lists `*-MD-TR.lis` files under `Data/BAMDataset_v032026/` and other discoverable folders |
| **Convert LIS → JSON** | Invokes `translate_bam_data_v2.py` as subprocess; saves output JSON |
| **Load & validate** | Loads JSON, runs required-path check + full JSON Schema validation, shows counts |
| **Tree view** | Renders JSON against schema as an expandable HTML tree (`tree_html_from_schema()`) |
| **Validation highlighting** | Missing required fields in **red**, present required fields in **green** |
| **Auto-fix** | Button triggers `autofix_schema_errors()` and saves a fixed JSON |
| **SHACL validation** | Upload or select TTL data graph and shapes graph; runs `shacl_validation_core` |
| **Jump-to-field anchors** | Each tree node has an HTML `id` derived from its JSON path |

### `tree_html_from_schema()` rendering rules

- Resolves `$ref`, `oneOf`/`anyOf` (picks the branch matching the data type), `allOf` (merges properties)
- Branch nodes (objects with properties) rendered as `<details open>` expandable sections
- Leaf nodes rendered as `key: value` with color-coded validation markers
- Arrays: single-item arrays skip the `[0]` wrapper layer; multi-item arrays show collapsible `[n]` items
- Empty/null values shown as `(empty)` in red; absent optional fields as `(not provided)` in grey

---

## 9. RDF / SHACL Pipeline

**Scripts:** `Parsing/bin/bam2shacl.py`, `json_to_shacl.py`, `json_to_shacl_2.py`, `shacl_validation_core.py`, `validate_rdf_shacl.py`  
**Example files:** `Parsing/shacl_validation/rdfGraph_smallExample.ttl`, `shaclShape_smallExample.ttl`

### Workflow

1. **JSON → RDF Turtle** — `bam2shacl.py` / `json_to_shacl.py` convert the JSON experiment document to a knowledge-graph Turtle file
2. **SHACL validation** — `shacl_validation_core.run_shacl_validation(data_ttl, shapes_ttl)` uses `pyshacl` + `rdflib`
3. **Output** — Returns `{conforms: bool, results: [...], report_text: str}`

### SHACL shape generation

`Parsing/dependencies/creep_shacl_maker/` contains tools to derive SHACL shapes from the JSON Schema.

---

## 10. RDF Visualization Web App (Flask)

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

## 11. Demonstrator App (Streamlit)

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

## 12. Data Download from Zenodo

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
| `18933930` | Current/latest dataset |
| `13937987` | Legacy v1 dataset |

---

## 13. Batch Processing

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

## 14. Tests

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

## 15. Environment & Dependencies

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

## 16. End-to-End Workflow Summary

```
Step 1 — Download data (optional)
  python Parsing/bin/get_data_from_zenodo.py
  → Parsing/Data/BAMDataset/

Step 2 — Parse a LIS file
  ParserV2("Vh5205_C-78-MD-TR.lis").parse_lis()
  → hierarchical dict (metadata / primary_data / secondary_data / data)

Step 3 — Translate to JSON experiment document
  python Parsing/bin/translate_bam_data_v2.py Vh5205_C-78-MD-TR.lis
  → Vh5205_C-78-MD-TR_schema_v2.json
    (conforms to Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json)

Step 4 — Validate JSON
  validation_core.validate_required_keywords(schema, doc)
  → missing-field warnings list
  validation_core.run_jsonschema_validation(schema, data)
  → full schema errors list

Step 5 — Interactive validation in web app
  python Parsing/bin/metadata_validation_web_app.py
  → open http://127.0.0.1:8503
  - Pick LIS file → Convert → inspect tree → highlight missing fields → auto-fix

Step 6 — Convert to RDF and validate with SHACL
  python Parsing/bin/bam2shacl.py ...
  python Parsing/bin/validate_rdf_shacl.py ...

Step 7 — Visualize RDF graph
  python Parsing/bin/visualization_web_app.py
  → open http://127.0.0.1:8502
```

### Current dataset specimens (v032026)

Tests: **C-78, C-80, C-81, C-82, C-85, C-89, C-91, C-94, C-95, C-97, C-98, C-99**  
Material: CMSX-6 single-crystal Ni-base superalloy  
Temperatures: ~980 °C, stress levels: ~200–300 MPa  
DOI: https://doi.org/10.1016/j.dib.2025.112436
