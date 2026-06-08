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

## Translator changes (translate_bam_data_v2.py)

- **`_try_other_detection` now validates non-`*Options` enum fields:** previously only `*Options` dropdown fields were checked against the schema enum; all other enum-constrained fields were silently passed through unchanged. Now all enum-constrained fields are validated with an exact match; a mismatch logs an `ERROR` and the raw LIS value is written to the JSON.
- **Exact suffix_map key for `testPieceTypeI`:** changed `"specimen according to din en iso"` (partial, unreachable) to `"specimen according to din en iso 204:2019-4"` (exact LIS value) to correctly normalise to `"Specimen according to standard"`.
