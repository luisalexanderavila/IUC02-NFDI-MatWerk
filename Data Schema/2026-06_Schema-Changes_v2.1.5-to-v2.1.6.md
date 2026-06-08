# Schema changelog: v2.1.5 → v2.1.6

**Date:** 2026-06-08

## Changes

### 1. `interruptionCourse` — added "Not applicable"

**Path:** `MeasurementData.AdditionalMetadata.TestInfo.testParameters.interruptionCourse`

Added `"Not applicable"` to the enum. Uninterrupted creep tests do not have an interruption course; the LIS files record `"Not applicable"` for these experiments.

**Before:** `["Unloading before cooling", "Unloading after cooling"]`  
**After:** `["Unloading before cooling", "Unloading after cooling", "Not applicable"]`

### 2. `fracturePosition` — added "Not applicable"

**Path:** `MeasurementData.PrimaryData.TestResult.valuesRecordedAfterTestEnd.fracturePosition`

Added `"Not applicable"` to the enum. Tests where fracture did not occur (or was not measured) record `"Not applicable"` in the LIS files.

**Before:** 9 fracture position options  
**After:** same 9 options + `"Not applicable"`

### 3. `TestPiece` — added `testPieceTypeIStandard` conditional field

**Path:** `MeasurementData.AdditionalMetadata.TestPiece`

Added an `allOf` conditional to `TestPiece`: when `testPieceTypeI == "Specimen according to standard"`, the field `testPieceTypeIStandard` (string) is made available to record the specific standard reference (e.g. `"DIN EN ISO 204:2019-4"`).

This mirrors the LIS file content which specifies the full standard reference (e.g. `"Specimen according to DIN EN ISO 204:2019-4"`). The translator normalises the LIS value to the enum option and stores the original reference in `testPieceTypeIStandard`.

## Translator changes (translate_bam_data_v2.py)

- **`_try_other_detection` now validates non-`*Options` enum fields:** previously only `*Options` dropdown fields were checked against the schema enum; all other enum-constrained fields were silently passed through unchanged. Now all enum-constrained fields are validated with an exact match; a mismatch logs an `ERROR` and the raw LIS value is written to the JSON.
- **`testPieceTypeI` sibling extraction:** when the LIS value starts with `"Specimen according to "` but is not exactly `"Specimen according to standard"`, the original value is stored in `testPieceTypeIStandard` and the normalised enum value `"Specimen according to standard"` is written to `testPieceTypeI`.
- **Exact suffix_map key for `testPieceTypeI`:** changed `"specimen according to din en iso"` (partial, unreachable) to `"specimen according to din en iso 204:2019-4"` (exact LIS value) and corrected the suffix_map key casing from `testPiece.` to `TestPiece.` (PascalCase match).
