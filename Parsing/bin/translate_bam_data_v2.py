"""
translate_bam_data_v2.py - Convert a v2 BAM LIS file to a JSON conforming to
the 2026-03 data schema (v2.1).

Usage:
    python translate_bam_data_v2.py <path/to/file.lis> [-o output.json]

The script:
1. Detects whether the LIS file is v1 (old) or v2 (new 2026 format).
2. Parses the LIS file using the appropriate parser.
3. Applies the mapping document (BAM2schema_v2.json) to produce a JSON that
    mirrors the 2026-03_Data-Schema_Creep_v2.1.json structure.
4. Writes the output JSON file.
"""

import json
import os
import re
import sys
import logging
import argparse
import importlib.util

# Ensure the dependencies are importable when run from the Parsing directory
_script_dir = os.path.dirname(os.path.abspath(__file__))
_parsing_root = os.path.dirname(_script_dir)
_deps_dir = os.path.join(_parsing_root, "dependencies")
for _dep in ["LISParser", "Mappingsreader"]:
    _dep_path = os.path.join(_deps_dir, _dep)
    if _dep_path not in sys.path:
        sys.path.insert(0, _dep_path)

_lisparser_module_dir = os.path.join(_deps_dir, "LISParser", "LISParser")
if _lisparser_module_dir not in sys.path:
    sys.path.insert(0, _lisparser_module_dir)

_lisparse_v2_file = os.path.join(_lisparser_module_dir, "LisParseV2.py")
_spec = importlib.util.spec_from_file_location("LisParseV2", _lisparse_v2_file)
if _spec is None or _spec.loader is None:
    raise ImportError(f"Unable to load LisParseV2 from {_lisparse_v2_file}")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
ParserV2 = _module.ParserV2

logging.basicConfig(level=logging.INFO)
Logger = logging.getLogger(__name__)

DEFAULT_MAPPING_FILE = os.path.join(_parsing_root, "Metadata", "Mappings", "BAM2schema_v2.json")
DEFAULT_SCHEMA_FILE = os.path.join(_parsing_root, "..", "Data Schema", "2026-06_Data-Schema_Creep_v2.1.5.json")


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _set_nested(d: dict, keys: list, value):
    """Set d[keys[0]]...[keys[-1]] = value, creating dicts as needed.
    If a key is a decimal-integer string (e.g. '0'), treat the parent as a list.
    """
    for k in keys[:-1]:
        if k.isdigit():
            # the parent should be a list; 'd' here is that parent
            idx = int(k)
            # we can't do much with pure dicts here; expand to index
            # For simplicity store as dict with int keys, convert at end
            d = d.setdefault(int(k), {})
        else:
            d = d.setdefault(k, {})
    last = keys[-1]
    if last.isdigit():
        d[int(last)] = value
    else:
        d[last] = value


def _set_nested_safe(d: dict, keys: list, value):
    """
    Navigate/create the nested dict structure along `keys`, then set the leaf.
    Handles integer-like keys by keeping them as int (for array-like nodes).
    """
    node = d
    for k in keys[:-1]:
        actual_key = int(k) if k.isdigit() else k
        if actual_key not in node:
            node[actual_key] = {}
        node = node[actual_key]
    last = int(keys[-1]) if keys[-1].isdigit() else keys[-1]
    node[last] = value


def _set_default_sibling_if_missing(root: dict, schema_keys: list, sibling_key: str, sibling_value):
    """Set a sibling leaf if parent exists and sibling is currently missing."""
    if len(schema_keys) < 2:
        return

    parent = root
    for k in schema_keys[:-1]:
        actual_key = int(k) if k.isdigit() else k
        if not isinstance(parent, dict) or actual_key not in parent:
            return
        parent = parent[actual_key]

    if isinstance(parent, dict) and sibling_key not in parent:
        parent[sibling_key] = sibling_value


def _normalize_mapping_key(key: str) -> str:
    """Normalize dot-path keys from LIS and mapping files for robust lookup."""
    parts = [segment.strip().casefold() for segment in key.split(".")]
    return ".".join(parts)


def _normalize_yes_no(raw: str):
    text = raw.strip()
    low = text.casefold()
    if low.startswith("yes"):
        return "Yes"
    if low.startswith("no"):
        return "No"
    return None


def _normalize_value_for_schema_path(schema_path: str, raw_value: str):
    """Normalize known LIS value variants to schema enum vocabulary for v2.0."""
    value = raw_value.strip()
    path = schema_path
    low = value.casefold()

    suffix_map = {
        "asManufacturedMaterial.condition": {
            "heat treated": "Heat treated",
            "as manufactured": "As manufactured",
        },
        "asManufacturedMaterial.solidification": {
            "single crystal": "Single crystal",
            "polycrystal": "Polycrystal",
        },
        "testParameters.loadControlType": {
            "constant force": "Constant Force",
            "constant stress": "Constant Stress",
        },
        "testParameters.testStandard.testStandardOptions": {
            "iso 204": "ISO 204",
            "astm e139": "ASTM E139",
        },
        "testMachine.testMachineType.testMachineTypeOptions": {
            "lever arm": "Lever arm",
            "electromechanical drive": "Electromechanical drive",
        },
        # "astm e220" removed: "ASTM E220-19" (versioned) was caught via startswith,
        # silently mapping to "ASTM E220". Versioned references route to Other via B6.
        "temperatureSensor.calibrationStandard.calibrationStandardOptions": {},
        "testPiece.testPieceTypeI": {
            "specimen according to standard": "Specimen according to standard",
            "specimen according to din en iso": "Specimen according to standard",
            "miniaturized specimen": "Miniaturized specimen",
        },
        "testMachine.heatingSystem.furnaceType.furnaceTypeOptions": {
            "split tube furnace with two-zones": "Split Tube Furnace with Two-zones",
            "split tube furnace with three-zones": "Split Tube Furnace with Three-zones",
        },
        # elongationValues and crossSectionalDimensions were previously a combined section;
        # now split into separate schema paths.
        "elongationValues.measuringEquipment.measuringEquipmentOptions": {
            "measuring microscope": "Measuring microscope",
            "caliper gauge": "Caliper gauge",
        },
        "crossSectionalDimensions.measuringEquipment.measuringEquipmentOptions": {
            "micrometer": "Micrometer screw gauge",
            "measuring microscope": "Measuring microscope",
        },
        "elongationValues.type.typeOptions": {
            "optical": "Analog",
            "digital": "Digital",
            "analog": "Analog",
        },
        "crossSectionalDimensions.type.typeOptions": {
            "optical": "Analog",
            "digital": "Digital",
            "analog": "Analog",
        },
        "temperatureSensor.thermocoupleLocation": {
            "inside the gauge length": "Inside",
            "inside": "Inside",
            "outside": "Outside",
        },
        "materialHistoryAndCondition.microstructure.0.microstructureFeature.microstructureFeatureOptions": {
            "matrix": "Matrix",
            "phase": "Phase",
            "grain boundary": "Grain Boundary",
            "dendrite": "Dendrite",
            "precipitate": "Precipitate",
            "inclusion": "Inclusion",
            "grain": "Grain",
            "segregation": "Segregation",
            "microstructure before testing": "Matrix",
        },
        "microstructureNi-BasedSX.grainSizeDeterminationMethod.grainSizeDeterminationMethodOptions": {
            "line intercept": "Line Intercept",
            "circular intercept": "Circular Intercept",
            # "not applicable" intentionally omitted: routes to Other via B6
        },
        # "extensometerSystem.sensorTypeContactingMethod.sensorTypeContactingMethodOptions" removed:
        # "High-Temperature Axial Extensometer" is not semantically equivalent to any enum option
        # and is handled correctly by B6 Other-detection.
        # "elongationValuesAndCrossSectionalDimensions.type.typeOptions" removed — outdated
        # combined path. Replaced above by separate elongationValues / crossSectionalDimensions entries.
        # "materialHistoryAndCondition.heatTreatment.heatTreatmentState.heatTreatmentStateOptions"
        # removed — dead code: PascalCase path never matched camelCase suffix key.
        # "Aged" is not an exact match for any enum option and is handled by B6 Other-detection.
        "extensionValues.contactingExtensometer.extensionAveraging": {
            "yes": "Yes",
            "no": "No",
            "not applicable": "Not applicable",
        },
    }

    for suffix, candidates in suffix_map.items():
        if path.endswith(suffix):
            for source, target in candidates.items():
                if low == source:
                    return target
                if low.startswith(source):
                    return target

    return value


def _fix_int_keys(obj):
    """Recursively replace integer keys with a proper list where appropriate."""
    if isinstance(obj, dict):
        # Check if all keys are consecutive integers starting at 0
        int_keys = sorted(k for k in obj if isinstance(k, int))
        str_keys = [k for k in obj if isinstance(k, str)]
        if int_keys and not str_keys and int_keys == list(range(len(int_keys))):
            return [_fix_int_keys(obj[i]) for i in int_keys]
        return {k: _fix_int_keys(v) for k, v in obj.items()}
    return obj


def _extract_quoted_file_reference(text: str):
    """Extract filename from a value like: See file "name.lis"."""
    m = re.search(r'"([^"]+)"', text)
    return m.group(1).strip() if m else None


def _parse_chemical_composition_file(file_path: str, measured: bool):
    """Parse complementary chemical composition LIS tables into schema items.

    Returns:
        tuple[list[dict], list[str]]: Parsed composition rows and unique methods
        (method list is only populated for measured composition files).
    """
    if not os.path.isfile(file_path):
        return [], []

    rows = []
    methods = []
    # Complementary LIS files can be UTF-8 or latin1; try UTF-8 first.
    try:
        raw_bytes = open(file_path, "rb").read()
        raw_bytes.decode("utf-8")
        _enc = "utf-8"
    except UnicodeDecodeError:
        _enc = "latin1"
    with open(file_path, "r", encoding=_enc) as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line:
                continue
            if line.lower().startswith("symbol\t"):
                continue

            cols = [c.strip() for c in line.split("\t")]
            if len(cols) < 3:
                continue

            element = cols[0]
            unit = cols[1]
            if not element:
                continue

            if measured:
                # Symbol | Unit | Measured Value | Method | Equipment
                value = cols[2].strip() if len(cols) > 2 else ""
                method = cols[3].strip() if len(cols) > 3 else ""
                equipment = cols[4].strip() if len(cols) > 4 else ""
            else:
                # Symbol | Unit | Min. | Max.
                min_value = cols[2].strip() if len(cols) > 2 else ""
                max_value = cols[3].strip() if len(cols) > 3 else ""
                if min_value and max_value:
                    value = f"{min_value} - {max_value}"
                else:
                    value = min_value or max_value

            if not value:
                continue

            row = {
                "element": element,
                "value": value,
                "unit": unit,
            }

            if measured:
                if method:
                    row["measurementMethod"] = method
                    methods.append(method)
                if equipment:
                    row["equipment"] = equipment

            rows.append(row)

    unique_methods = list(dict.fromkeys(methods))
    return rows, unique_methods


def _build_enum_lookup(schema: dict) -> dict:
    """Walk the schema and build a map of dot-path suffix -> allowed enum values.

    Only collects paths that end in '*Options' (dropdown fields), since those
    are the candidates for "Other" auto-detection.

    Returns:
        dict mapping lowercase dot-path suffix (e.g. 'testStandard.testStandardOptions')
        to list of allowed string values.
    """
    result = {}

    def _walk(node, path_parts):
        if not isinstance(node, dict):
            return
        if "enum" in node and isinstance(node["enum"], list):
            key = ".".join(path_parts)
            # Collect all string enum values
            result[key] = [v for v in node["enum"] if isinstance(v, str)]
        for prop_name, prop_val in node.get("properties", {}).items():
            _walk(prop_val, path_parts + [prop_name])
        for item in node.get("allOf", []):
            _walk(item, path_parts)
        for item in node.get("anyOf", []):
            _walk(item, path_parts)
        if "then" in node:
            _walk(node["then"], path_parts)
        if "items" in node:
            _walk(node["items"], path_parts)

    _walk(schema, [])
    return result


_OTHER_OPTION_PREFIX = "Other (Please specify in the comment)"
_OTHER_FIELD_PREFIX = "other"


def _try_other_detection(schema_path: str, value: str, enum_lookup: dict) -> tuple:
    """Check if value matches any enum option for this *Options path.

    If NOT matched and "Other" is in the enum, return:
        ("Other (Please specify in the comment)", actual_value_for_other_field, other_field_name)
    Otherwise return (value, None, None).
    """
    if not schema_path.endswith("Options"):
        return value, None, None

    # Find the matching suffix in enum_lookup
    allowed = None
    for suffix, options in enum_lookup.items():
        if schema_path.endswith(suffix):
            allowed = options
            break
    if allowed is None:
        return value, None, None

    # Check if value already matches (case-insensitive)
    low = value.strip().casefold()
    for opt in allowed:
        if low == opt.casefold():
            return value, None, None  # already matches

    # Does the enum have an "Other" option?
    other_opt = next((o for o in allowed if o.startswith(_OTHER_OPTION_PREFIX[:5])), None)
    if other_opt is None:
        return value, None, None

    # Derive the other field name: strip trailing "Options" → prepend "other"
    base = schema_path.rsplit(".", 1)[-1]  # e.g. "testStandardOptions"
    base_without_options = base[: -len("Options")]  # e.g. "testStandard"
    other_field = _OTHER_FIELD_PREFIX + base_without_options[0].upper() + base_without_options[1:]
    # e.g. "otherTestStandard"

    return other_opt, value, other_field


def translate_v2(parsed: dict, mapping_doc: dict, source_lis_file: str = "",
                 schema_file: str = "") -> dict:
    """
    Apply the v2 mapping document to the v2 parsed LIS output and produce a
    schema-conforming nested dict.

    The parsed dict has records like:
        parsed["metadata"]["Test info"]["Test job details"]["Date of test start"]
            = {"value": "...", "unit": "", "symbol": "", ...}

    The mapping_doc["mappedMeasurementData"] maps flat dot-separated keys
    (e.g. "metadata.Test info.Test job details.Date of test start") to schema
    paths (e.g. "MeasurementData.additionalMetadata.testInfo.testJobDetails.dateOfTestStart").

    schema_file: optional path to the JSON schema. When provided, enables
        automatic "Other" detection for *Options dropdown fields.
    """
    mapping = mapping_doc.get("mappedMeasurementData", {})
    result = {}

    # Build enum lookup for "Other" auto-detection
    enum_lookup: dict = {}
    if schema_file and os.path.isfile(schema_file):
        try:
            with open(schema_file, "r", encoding="utf-8") as _sf:
                _schema_doc = json.load(_sf)
            enum_lookup = _build_enum_lookup(_schema_doc)
        except Exception:
            pass

    flat_records = {}

    def _flatten_records(node, prefix=""):
        if not isinstance(node, dict):
            return
        for key, value in node.items():
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict) and "value" in value:
                flat_records[full_key] = value
                flat_records[_normalize_mapping_key(full_key)] = value
            else:
                _flatten_records(value, full_key)

    for section_name in ("metadata", "primary_data", "secondary_data"):
        _flatten_records(parsed.get(section_name, {}), section_name)

    source_dir = os.path.dirname(os.path.abspath(source_lis_file)) if source_lis_file else ""

    for lis_key, schema_path in mapping.items():
        record = flat_records.get(lis_key)
        if record is None:
            record = flat_records.get(_normalize_mapping_key(lis_key))
        if record is None:
            continue
        if isinstance(record, dict) and "value" in record:
            raw_value = record["value"]
        else:
            # Could be a non-leaf or an unexpected structure
            raw_value = str(record) if record else ""

        if not raw_value:
            continue

        # Extract inline sub-properties before normalizing the enum value.
        # Pattern: "<EnumOption>, <PropertyName> <PropertyValue>"
        # Currently handled: testMachineTypeOptions with "Leverage ratio X:Y"
        _extra_sibling = None
        if schema_path.endswith("testMachineType.testMachineTypeOptions"):
            _leverage_match = re.search(r",\s*Leverage ratio\s+(.+)$", raw_value, re.IGNORECASE)
            if _leverage_match:
                _extra_sibling = ("leverageRatio", _leverage_match.group(1).strip())
                raw_value = raw_value[: _leverage_match.start()].strip()

        raw_value = _normalize_value_for_schema_path(schema_path, raw_value)

        schema_keys = schema_path.split(".")

        _is_chem_comp = (
            ".chemicalCompositionNominal." in schema_path
            or ".chemicalCompositionMeasured." in schema_path
        )

        # If composition points to an external LIS file, try to parse and inline it.
        # Fall back to ChemicalCompositionExternalFile if parsing is not possible.
        if _is_chem_comp and raw_value.strip().lower().startswith("see file"):
            _external_link = _extract_quoted_file_reference(raw_value) or raw_value.strip()
            _is_measured = ".chemicalCompositionMeasured." in schema_path

            parsed_rows = []
            parsed_methods = []
            if source_dir:
                _external_path = os.path.join(source_dir, _external_link)
                parsed_rows, parsed_methods = _parse_chemical_composition_file(
                    _external_path,
                    measured=_is_measured,
                )

            for _comp_key in ("chemicalCompositionNominal", "chemicalCompositionMeasured"):
                if _comp_key in schema_keys:
                    _parent_keys = schema_keys[:schema_keys.index(_comp_key) + 1]
                    if parsed_rows:
                        _set_nested_safe(result, _parent_keys, parsed_rows)

                        # For measured compositions, derive top-level measurementMethod
                        # from the complementary file when that field is not present
                        # in the main LIS mapping.
                        if _is_measured and parsed_methods:
                            _method_value = "; ".join(parsed_methods)
                            _composition_parent_keys = schema_keys[:schema_keys.index(_comp_key)]
                            _set_default_sibling_if_missing(
                                result,
                                _composition_parent_keys + ["_placeholder"],
                                "measurementMethod",
                                _method_value,
                            )
                    else:
                        _set_nested_safe(result, _parent_keys, {"externalFileLink": _external_link})
                    break
        else:
            # B6 — "Other" auto-detection for *Options dropdown fields.
            # If value doesn't match any known enum option and the enum has an
            # "Other (Please specify in the comment)" option, use that and write
            # the actual LIS value into the corresponding other* sibling field.
            _other_value = None
            _other_field = None
            if enum_lookup:
                raw_value, _other_value, _other_field = _try_other_detection(
                    schema_path, raw_value, enum_lookup
                )

            _set_nested_safe(result, schema_keys, raw_value)

            if _other_value is not None and _other_field is not None:
                _set_nested_safe(result, schema_keys[:-1] + [_other_field], _other_value)

            # Write any inline sub-property extracted before normalization
            # (e.g. leverageRatio from "Lever arm, Leverage ratio 1:20.4")
            if _extra_sibling is not None:
                _sibling_name, _sibling_value = _extra_sibling
                _set_nested_safe(result, schema_keys[:-1] + [_sibling_name], _sibling_value)

            # When the mapping target is a ComplexValue leaf (path ends in
            # ".value"), also write the sibling ".unit" from the LIS record.
            if schema_keys[-1] == "value" and isinstance(record, dict):
                unit = record.get("unit", "").strip()
                if unit:
                    # B7 — strip trailing unit from value to avoid duplication
                    # (e.g. wireGauge value "0.51 mm" with unit "mm" → value "0.51")
                    if raw_value.endswith(" " + unit):
                        raw_value = raw_value[: -(len(unit) + 1)].strip()
                        _set_nested_safe(result, schema_keys, raw_value)
                    _set_nested_safe(result, schema_keys[:-1] + ["unit"], unit)

            # Chemical composition items in schema require an `element` field.
            # LIS files often provide a file reference or aggregate text, not per-element rows.
            # Create a minimal placeholder so the converted structure is schema-complete.
            if _is_chem_comp:
                _set_default_sibling_if_missing(result, schema_keys, "element", "unspecified")

    return _fix_int_keys(result)


def validate_against_schema(data: dict, schema_file: str):
    """Validate data against the JSON schema and return a list of error dicts."""
    from jsonschema import Draft201909Validator

    with open(schema_file, "r", encoding="utf-8") as fh:
        schema = json.load(fh)

    errors = []
    validator = Draft201909Validator(schema)
    for err in validator.iter_errors(data):
        path = "/".join(str(p) for p in err.absolute_path)
        errors.append({
            "path": path,
            "message": err.message,
        })

    errors.sort(key=lambda e: (e["path"], e["message"]))
    return errors


# ─── Main ─────────────────────────────────────────────────────────────────────

def _build_arg_parser():
    parser = argparse.ArgumentParser(
        prog="translate_bam_data_v2.py",
        description="Translate a BAM v2 LIS file to schema 2025-12 JSON",
    )
    parser.add_argument("filename", help="Input LIS file", type=str)
    parser.add_argument(
        "--output", "-o",
        dest="output",
        help="Output file name. Defaults to <input>_schema_v2.json.",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--mapping", "-m",
        dest="mapping",
        help="Mapping document. Defaults to Metadata/Mappings/BAM2schema_v2.json.",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--validate-schema",
        dest="schema_file",
        help="Validate output JSON against this schema file.",
        type=str,
        default=None,
    )
    parser.add_argument(
        "--validation-report",
        dest="validation_report",
        help="Optional path to write schema-validation errors as JSON.",
        type=str,
        default=None,
    )
    return parser


def main(argv=None):
    args = _build_arg_parser().parse_args(argv)

    mapping_file = args.mapping if args.mapping else DEFAULT_MAPPING_FILE
    schema_file = args.schema_file if args.schema_file else DEFAULT_SCHEMA_FILE

    Logger.info(f"Input  : {args.filename}")
    Logger.info(f"Mapping: {mapping_file}")

    # Load mapping
    with open(mapping_file, "r", encoding="utf-8-sig") as fh:
        mapping_doc = json.load(fh)

    # Parse LIS
    parser = ParserV2(args.filename)
    parsed = parser.parse_lis()

    lis_version = parsed.get("lis_version", "unknown")
    schema_version = parsed.get("schema_version", "unknown")
    Logger.info(f"Detected LIS version  : {lis_version}")
    Logger.info(f"Detected schema version: {schema_version}")

    if lis_version == "v1":
        Logger.warning(
            "This file was detected as v1 (old format). "
            "Use translate_bam_data.py for v1 files instead."
        )

    # Translate
    output_dict = translate_v2(parsed, mapping_doc, source_lis_file=args.filename,
                               schema_file=schema_file)

    # Inject version metadata
    output_dict["_lis_version"] = lis_version
    output_dict["_schema_version"] = schema_version
    output_dict["_source_file"] = os.path.basename(args.filename)

    # Write output
    if args.output:
        outfile = args.output
    else:
        base = os.path.splitext(args.filename)[0]
        outfile = base + "_schema_v2.json"

    with open(outfile, "w", encoding="utf-8") as fh:
        json.dump(output_dict, fh, indent=4, ensure_ascii=False)

    Logger.info(f"Output written to: {outfile}")

    if args.schema_file:
        errors = validate_against_schema(output_dict, schema_file)
        Logger.info(f"Schema validation errors: {len(errors)}")
        for err in errors:
            Logger.error(f"{err['message']} @ {err['path']}")

        if args.validation_report:
            report = {
                "source_file": os.path.basename(args.filename),
                "output_file": outfile,
                "schema_file": schema_file,
                "error_count": len(errors),
                "errors": errors,
            }
            with open(args.validation_report, "w", encoding="utf-8") as fh:
                json.dump(report, fh, indent=2, ensure_ascii=False)
            Logger.info(f"Validation report written to: {args.validation_report}")

        if errors:
            return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
