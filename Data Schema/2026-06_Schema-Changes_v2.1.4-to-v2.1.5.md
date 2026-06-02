# Schema Change Report: v2.1.4 → v2.1.5

**Date:** 2026-06-02  
**Source file:** `2026-05_Data-Schema_Creep_v2.1.4.json`  
**Output file:** `2026-06_Data-Schema_Creep_v2.1.5.json`  

---

## Summary

`loadingSystem.calibrationStandard` was changed from a plain enum string to a structured object, consistent with other dropdown fields in the schema (e.g. `measuringEquipment`, `testMachineType`). This allows versioned or non-standard calibration standard references (e.g. `"DIN EN ISO 7500-2: 2007"`) to be captured as `"Other"` with the actual value stored in a dedicated sibling field.

---

## Changes

### 1. `MeasuringAndTestEquipment.testMachine.loadingSystem.calibrationStandard`

Changed from a flat string enum to an object with a `calibrationStandardOptions` property and an `allOf` conditional that requires `otherCalibrationStandard` when `"Other (Please specify in the comment)"` is selected.

**Before:**
```json
"calibrationStandard": {
  "type": "string",
  "enum": [
    "DIN EN ISO 7500-2",
    "Other (Please specify in the comment)"
  ]
}
```

**After:**
```json
"calibrationStandard": {
  "type": "object",
  "properties": {
    "calibrationStandardOptions": {
      "type": "string",
      "enum": [
        "DIN EN ISO 7500-2",
        "Other (Please specify in the comment)"
      ]
    }
  },
  "allOf": [
    {
      "if": {
        "properties": {
          "calibrationStandardOptions": {
            "const": "Other (Please specify in the comment)"
          }
        }
      },
      "then": {
        "required": ["otherCalibrationStandard"],
        "properties": {
          "otherCalibrationStandard": {
            "type": "string"
          }
        }
      }
    }
  ]
}
```

---

## Motivation

LIS files in the BAMDataset_v052026 dataset contain calibration standard references including the year of the standard edition (e.g. `"DIN EN ISO 7500-2: 2007"`). The previous flat string enum did not accommodate versioned references as they do not exactly match the base enum option `"DIN EN ISO 7500-2"`. The new object structure allows:

- Exact matches (e.g. `"DIN EN ISO 7500-2"`) to be stored directly as `calibrationStandardOptions`.
- Versioned or non-listed references to be stored as `calibrationStandardOptions: "Other (Please specify in the comment)"` with the full original string in `otherCalibrationStandard`.

This pattern is already used throughout the schema for other equipment dropdown fields.

---

## What was NOT changed

- All other fields in `loadingSystem`
- All other sections of the schema
- `$defs`, `required` arrays, and schema metadata (`$schema`, `$id`, `title`, `description`)
