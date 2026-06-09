# IUC02 Copilot Working Instructions

This file guides AI agents working on the IUC02 codebase. Read this before making any changes.

## Current state (2026-06-09)

| Artefact | Current value |
|---|---|
| Active schema | `Data Schema/2026-06_Data-Schema_Creep_v2.1.8.json` |
| Active LIS dataset | `Parsing/Data/BAMDataset_v20260608/` (12 MD-TR files) |
| JSON output folder | `Parsing/Data/BAMDataset_Json/` |
| Translator default | `Parsing/bin/translate_bam_data_v2.py` line ~49 `DEFAULT_SCHEMA_FILE` |
| Active branch | `Parsing_Scripts` |
| Python env | `C:\Users\maria\anaconda3\envs\python311\python.exe` |

## Running the translator (batch)

```powershell
# From Parsing/ directory:
$py = "C:\Users\maria\anaconda3\envs\python311\python.exe"
foreach ($f in Get-ChildItem "Data\BAMDataset_v20260608\*-MD-TR.lis") {
    $out = "Data\BAMDataset_Json\$($f.BaseName)_translated.json"
    & $py bin\translate_bam_data_v2.py $f.FullName -o $out
}
```

After any change to LIS files, the schema, or the mapping — regenerate all JSONs with the above.

## Running the web app

```powershell
$py = "C:\Users\maria\anaconda3\envs\python311\python.exe"
cd C:\Users\maria\Desktop\IUC02\iuc02\Parsing
& $py bin\metadata_validation_web_app.py
# open http://127.0.0.1:8503
```

## Running tests

```powershell
cd C:\Users\maria\Desktop\IUC02\iuc02\Parsing
& "C:\Users\maria\anaconda3\envs\python311\python.exe" -m pytest test/ -q
```

## Enum handling rules — do not break these

All enum comparisons in `translate_bam_data_v2.py` are **exact and case-sensitive**. Do not add `casefold()` or `lower()` to enum comparisons.

1. If a LIS value exactly matches an enum option -> write it as-is.
2. If it does not match and the field has "Other (Please specify in the comment)" in its enum -> set `*Options = "Other..."` and write the raw value to the `other*` sibling.
3. If it does not match and there is NO "Other" option -> log `ERROR` and write the value as-is.
4. `suffix_map` entries normalize known LIS value variants **before** B6 checks. Only exact lowercase matches are used — no `startswith`.

## LIS file editing rules

- Encoding: **UTF-8 without BOM**, line endings: **CRLF**.
- Always read/write as binary to preserve CRLF: `open(path, 'rb')` / `open(path, 'wb')`.
- Do NOT use `encoding='utf-8-sig'` for LIS files — BOM breaks the v2 parser header detection.
- Column order (0-indexed): `CATEGORIZATION | ENTRY | ADDITIONAL_INFO | SYMBOL | UNIT | REQUIREMENT | VALUE | COMMON`
- When inserting new fields, match the tab structure of adjacent lines exactly.

## Mapping file (BAM2schema_v2.json)

- Encoding: **UTF-8 with BOM** — always open with `encoding='utf-8-sig'`.
- Structure: `{"mappedMeasurementData": {"lis.path.key": "Schema.Path.key", ...}}`
- Keys: all-lowercase, dot-separated LIS path.
- Values: dot-separated schema path starting with `MeasurementData`.
- suffix_map keys in the translator must use the **exact PascalCase** suffix from the schema path (e.g., `TestPiece.testPieceTypeI` not `testPiece.testPieceTypeI`).

## Schema versioning

When adding or changing schema fields:
1. Copy the current schema to a new version file (e.g., v2.1.7 -> v2.1.8).
2. Update `DEFAULT_SCHEMA_FILE` in `translate_bam_data_v2.py`.
3. Regenerate all JSONs.
4. If the web app has a hardcoded schema reference, update it too.

Schema property order matters for webapp rendering — the tree view renders fields in schema `properties` key order.

## Web app dropdown pattern

All dropdowns that should trigger a page refresh use `onchange="this.form.submit()"` and must have a `name` attribute. The schema dropdown uses `name="schema_path"`. Do not rely on JavaScript to copy values between elements before submitting.

## allOf + conditional fields in schema rendering

`_resolve_for_render()` in the web app merges allOf members. When modifying this function:
- Seed merged properties from the **node's own `properties`** first.
- Add allOf member `properties` (without overwriting).
- Add `then.properties` from `if/then` conditionals.
- This prevents nodes with only `if/then` allOf members from rendering as a raw JSON string.

## Commit conventions

Include the co-authored-by trailer:
```
Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>
```
