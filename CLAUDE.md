# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

NFDI-MatWerk Infrastructure Use Case IUC02: a framework for curating and distributing reference
datasets for creep testing of Ni-based single-crystal superalloys (CMSX-6). The repo covers the full
pipeline from raw lab instrument output to a validated, schema-conformant JSON document to an RDF
knowledge graph, plus two demo web apps.

Top-level areas:
- `Data Schema/` — versioned JSON Schema (Draft 2019-09) defining the experiment document structure.
  Current version is whichever `Data Schema/2026-*_Data-Schema_Creep_v*.json` has the highest version
  number; check `Data Schema/IntendedSchemaStructure.md` and the `*_Schema-Changes_*.md` changelogs
  before assuming a version. `working-files/` and `Zenodo/` hold prior/published versions — don't edit
  those, only the current top-level schema file.
- `Parsing/` — the actual pipeline: LIS/Excel parsers, JSON translators, JSON Schema + SHACL
  validators, two Flask web apps, and pytest tests. This is where most engineering work happens.
- `Demonstrator_App/` — public-facing Streamlit app (deployed at
  https://iuc-02-demonstrator.vercel.app) showing the workflow end-to-end for stakeholders.
- `New_app/IUC02_NextJS-main/IUC02_NextJS-main/` — a separate, newer Next.js (frontend) + FastAPI
  (backend) rewrite of the demonstrator, vendored wholesale (including its own `node_modules`-style
  `Scripts/`/`Lib/` venv). Treat it as its own project with its own README; not wired into `Parsing/`.
- `Knowledge-Graph-for-Creep-Reference-Datasets/` — maps published JSON datasets into the MSE
  Knowledge Graph (CTO ontology reuse). Driven by `creep_reference_dataset_map.sh`; SPARQL examples
  in `queries/`.
- `Reference_Data_Ontology_for_Creep/` — the RDOC ontology (`rdo_v1.rdf`) underlying the RDF/SHACL
  layer.

`SKILL.md` at the repo root is a detailed (Copilot-oriented) reference for the `Parsing/` pipeline. It
is generally accurate on data formats and workflow shape but its file names/paths sometimes lag actual
`Parsing/bin/` contents (e.g. it refers to `translate_bam_data_v2.py`/`LisParseV2.py`/`bam2shacl.py`,
which don't currently exist — the real files are `translate_bam_data.py`, `LisParse.py` (class
`ParserV2` inside it), `json_to_shacl.py`). When following it, verify the referenced file actually
exists in `Parsing/bin/` first.

## Commands

All `Parsing/` commands assume `cd Parsing` and the `python311` conda environment active
(`conda activate python311`; env is defined by `Parsing/environment.yaml`/`environment_w.yaml`).
Install/refresh deps with `pip install -r requirements.txt` (this installs the local
`dependencies/LISParser`, `dependencies/Mappingsreader`, `dependencies/creep_shacl_maker` packages
editably via `-e`).

Run tests:
```bash
pytest test/ -q
```
Run a single test:
```bash
pytest test/test_translate_bam_data.py::TestTranslateBamData::test_v2_conversion_creates_output -q
```

LIS → JSON (BAM dataset):
```bash
python bin/translate_bam_data.py Data/BAMDataset_v20260608/Vh5205_C-78-MD-TR.lis -o Data/BAMDataset_Json/Vh5205_C-78-MD-TR_translated.json
```

Excel → JSON (RUB dataset, all 41 tests at once):
```bash
python bin/translate_rub_data.py             # translate
python bin/translate_rub_data.py --download   # fetch source Excel from Zenodo first
python bin/translate_rub_data.py --validate   # also run schema validation
```
See `Parsing/Data/RUBDataset/CLAUDE.md` if present for RUB-pipeline-specific notes.

Validate a JSON document against the schema:
```bash
python bin/validate_json.py <path/to/experiment.json>
```

JSON → RDF Turtle, then SHACL validation:
```bash
python bin/json_to_shacl.py <input.json> -o <output.ttl>
python bin/validate_rdf_shacl.py ...
```

Batch translate + validate all BAM LIS files:
```bash
python bin/run_batch_validation.py
```

Interactive metadata validation web app (Flask, default port 8503):
```bash
python bin/metadata_validation_web_app.py
# Windows: bin\metadata_validation_web_app.bat
```

RDF graph visualization web app (Flask, default port 8502):
```bash
python bin/visualization_web_app.py
# Windows: bin\visualization_web_app_python311.bat
```

Download source data from Zenodo:
```bash
python bin/get_data_from_zenodo.py                                    # default record → Data/BAMDataset/
python bin/get_data_from_zenodo.py --zenodo-id 13937987 --output-dir Data/BAMDataset_legacy
```

One-shot "everything before handoff" (tests + visualization):
```bash
python bin/run_all_checks.py
# Windows: bin\run_all_checks.bat
```

Demonstrator app (Streamlit):
```bash
cd Demonstrator_App
conda activate python311
streamlit run IUC02_Demonstrator.py
```

New_app (Next.js + FastAPI rewrite) — see
`New_app/IUC02_NextJS-main/IUC02_NextJS-main/README.md` for its own `npm run dev` / `uvicorn` setup;
it's independent of the `Parsing/` conda environment.

## Architecture: the parsing/validation pipeline

```
BAM:  LIS file  →  LisParse.ParserV2  →  flat dict  →  BAM2schema*.json mapping  →  JSON experiment document
RUB:  Excel     →  pandas             →  test dict  →  hardcoded mapping in translate_rub_data.py →  JSON experiment document
                                                                                            ↓
                                                        validate against current Data Schema JSON Schema
                                                                                            ↓
                                                        json_to_shacl.py → RDF Turtle → pyshacl SHACL validation
```

- **LIS file format** (`Parsing/Data/BAMDataset*/*.lis`): tab-separated text, UTF-8 without BOM, CRLF
  line endings. Metadata rows have columns `CATEGORIZATION | ENTRY | ENTRY - ADDITIONAL INFORMATION |
  SYMBOL | UNIT | REQUIREMENT | INFORMATION | INFORMATION COMMON TO ALL (*)`; `CATEGORIZATION` is a
  `-->`-separated hierarchical path. A `[data]` marker starts the time-series data section (comma as
  decimal separator). Files without a `CATEGORIZATION` header are the legacy v1 format and get parsed
  differently. If you modify a LIS file programmatically, read/write it in binary mode and split on
  `b'\r\n'` — writing with `utf-8-sig` (BOM) breaks header detection.
- **Mapping documents** (`Parsing/Metadata/Mappings/BAM2schema*.json`) are flat, dot-separated
  lowercase LIS-path → dot-separated PascalCase/camelCase schema-path dictionaries; some are UTF-8
  **with BOM**, so open with `encoding="utf-8-sig"` when reading them directly.
- **Schema key convention**: top-level/section keys are PascalCase (`AdditionalMetadata`,
  `MeasuringAndTestEquipment`, ...), leaf field keys are camelCase.
- **"Other" dropdown pattern**: enum fields that allow a free-text override use a `*Options`/`other*`
  sibling pair, e.g. `testStandardOptions` (enum incl. `"Other (Please specify in the comment)"`) +
  `otherTestStandard` (string). When a LIS value doesn't match any enum option, the translator writes
  `*Options = "Other..."` and puts the raw value in `other*`; enum fields with no "Other" option log an
  ERROR on mismatch instead. This logic lives in `_try_other_detection` in `translate_bam_data.py`.
- **RUB pipeline known limitations** (see `translate_rub_data.py`): no specimen geometry or equipment
  detail, no chemical composition, strain is absolute not percentage, `typeOfLoading` is hardcoded to
  `"Constant Stress"`.
- `validation_core.py`'s `autofix_required_fields` has a known bug (overwrites existing non-dict leaf
  values with `{}` when a schema node has empty `properties`) — this is why `--autofill` in
  `translate_rub_data.py` defaults off; don't enable it until that's fixed.
- Validated JSON documents may appear in three shapes: bare (starting at `MeasurementData`), wrapped in
  `{"mappedMeasurementData": {...}}`, or using legacy camelCase top-level keys — `validation_core.
  normalize_experiment_data` handles all three.
