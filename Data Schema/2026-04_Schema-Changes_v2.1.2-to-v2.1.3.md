# Schema Change Report: v2.1.2 → v2.1.3

**Date:** 2026-04-23  
**Source file:** `2026-04_Data-Schema_Creep_v2.1.2.json`  
**Output file:** `2026-04_Data-Schema_Creep_v2.1.3.json`  

---

## Summary

In `PrimaryData.TestResult.valuesRecordedAtTestStart`, two generic fields were split into four more specific fields to distinguish reference-length calculations based on `Lo` and `Le`.

---

## Changes

### 1. `kValue` was replaced by:
- `kValue_LrLo`
- `kValue_LrLe`

Both keep the same description:
- `$L_{r}$ / square root of $S_{o}$.`

### 2. `ratioReferenceLengthToDiameter` was replaced by:
- `ratioReferenceLengthToDiameter_LrLo`
- `ratioReferenceLengthToDiameter_LrLe`

Both keep the same description:
- `$L_{r}$ / D.`

### 3. Updated required fields

**Before:**
```json
"kValue",
"ratioReferenceLengthToDiameter"

**After**
```json
"kValue_LrLo",
"kValue_LrLe",
"ratioReferenceLengthToDiameter_LrLo",
"ratioReferenceLengthToDiameter_LrLe"