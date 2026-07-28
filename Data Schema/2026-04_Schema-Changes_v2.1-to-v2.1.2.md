# Schema Change Report: v2.1 → v2.1.2

**Date:** 2026-04-09  
**Source file:** `2026-04_Data-Schema_Creep_v2.1.json`  
**Output file:** `2026-04_Data-Schema_Creep_v2.1.2.json`  
**Reference:** `IntendedSchemaStructure.md`

---

## Summary

The leaf-level field definitions and all `required` arrays within individual sections were correct and left unchanged. Only the **top-level structural hierarchy** was corrected to match the intended schema structure:

```
MeasurementData
 |- AdditionalMetadata
 |      |- TestInfo
 |      |- MaterialHistoryAndCondition
 |      |- TestPiece
 |      |- MeasuringAndTestEquipment
 |      '- DataProcessingProcedures
 |- PrimaryData
 |     '- TestResult
 '- SecondaryData
       '- TestResult
```

---

## Changes

### 1. `primaryData` and `secondaryData` moved into `MeasurementData`

**Before:** `primaryData` and `secondaryData` were placed as top-level siblings of `properties` at the root of the JSON Schema object (i.e., `schema.primaryData` and `schema.secondaryData`), outside of any property hierarchy.

**After:** Both are now nested as properties inside `MeasurementData`:
```
MeasurementData.properties.PrimaryData
MeasurementData.properties.SecondaryData
```

---

### 2. `testPiece`, `measuringAndTestEquipment`, `dataProcessingProcedures` moved into `AdditionalMetadata`

**Before:** These three sections were direct siblings of `additionalMetadata` inside `MeasurementData.properties`, i.e.:
```
MeasurementData.properties.additionalMetadata
MeasurementData.properties.testPiece              ← wrong level
MeasurementData.properties.measuringAndTestEquipment  ← wrong level
MeasurementData.properties.dataProcessingProcedures   ← wrong level
```

**After:** All three are nested inside `AdditionalMetadata.properties`:
```
MeasurementData.properties.AdditionalMetadata.properties.TestPiece
MeasurementData.properties.AdditionalMetadata.properties.MeasuringAndTestEquipment
MeasurementData.properties.AdditionalMetadata.properties.DataProcessingProcedures
```

---

### 3. `microstructureNi-BasedSX`, `chemicalComposition`, `ndtResults`, `mechanicalTestResults` moved into `MaterialHistoryAndCondition`

**Before:** These four sections were siblings of `materialHistoryAndCondition` inside `additionalMetadata.properties`, i.e.:
```
AdditionalMetadata.properties.materialHistoryAndCondition
AdditionalMetadata.properties.microstructureNi-BasedSX   ← wrong level
AdditionalMetadata.properties.chemicalComposition         ← wrong level
AdditionalMetadata.properties.ndtResults                  ← wrong level
AdditionalMetadata.properties.mechanicalTestResults       ← wrong level
```

**After:** All four are nested inside `MaterialHistoryAndCondition.properties`:
```
AdditionalMetadata.properties.MaterialHistoryAndCondition.properties.microstructureNi-BasedSX
AdditionalMetadata.properties.MaterialHistoryAndCondition.properties.chemicalComposition
AdditionalMetadata.properties.MaterialHistoryAndCondition.properties.ndtResults
AdditionalMetadata.properties.MaterialHistoryAndCondition.properties.mechanicalTestResults
```

---

### 4. Top-level section keys renamed to PascalCase

To match the naming convention in `IntendedSchemaStructure.md`, the following keys were renamed:

| Old key (camelCase) | New key (PascalCase) |
|---|---|
| `additionalMetadata` | `AdditionalMetadata` |
| `testInfo` (inside AdditionalMetadata) | `TestInfo` |
| `materialHistoryAndCondition` | `MaterialHistoryAndCondition` |
| `testPiece` | `TestPiece` |
| `measuringAndTestEquipment` | `MeasuringAndTestEquipment` |
| `dataProcessingProcedures` | `DataProcessingProcedures` |
| `primaryData` | `PrimaryData` |
| `secondaryData` | `SecondaryData` |
| `testResult` (in PrimaryData and SecondaryData) | `TestResult` |

---

### 5. `MeasurementData.required` updated

The `required` array of `MeasurementData` was updated to reflect the new PascalCase key names:

**Before:**
```json
"required": ["additionalMetadata", "primaryData", "secondaryData"]
```

**After:**
```json
"required": ["AdditionalMetadata", "PrimaryData", "SecondaryData"]
```

---

## What was NOT changed

- All leaf-level field definitions (types, enums, descriptions, `$ref`, `allOf`/`if`/`then` conditionals)
- All `required` arrays within individual sections (e.g., `testParameters`, `testPiece`, `loadingSystem`, etc.)
- All `$defs` entries (`ComplexValue`, `ChemicalCompositionElementsList`, etc.)
- Schema metadata (`$schema`, `$id`, `title`, `description`)
