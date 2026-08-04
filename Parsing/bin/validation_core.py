import copy
import json
from pathlib import Path


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def is_defined(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def resolve_ref(schema_root: dict, schema_node: dict) -> dict:
    ref = schema_node.get("$ref") if isinstance(schema_node, dict) else None
    if not ref or not ref.startswith("#/"):
        return schema_node

    target = schema_root
    for part in ref[2:].split("/"):
        target = target.get(part, {}) if isinstance(target, dict) else {}

    return target if isinstance(target, dict) else schema_node


def _normalize_legacy_chemical_composition_methods(data_target):
    """Map legacy chemical-composition element key `method` to `measurementMethod`."""
    if not isinstance(data_target, dict):
        return

    measurement_data = data_target.get("MeasurementData")
    if not isinstance(measurement_data, dict):
        return

    # Support both old camelCase key (legacy) and new PascalCase key (v2.1.2+).
    additional_metadata = measurement_data.get("AdditionalMetadata") or measurement_data.get("additionalMetadata")
    if not isinstance(additional_metadata, dict):
        return

    # chemicalComposition may live directly in additionalMetadata (v2.1 legacy)
    # or inside MaterialHistoryAndCondition (v2.1.2+).
    material_section = additional_metadata.get("MaterialHistoryAndCondition") or additional_metadata
    chemical_composition = material_section.get("chemicalComposition")
    if not isinstance(chemical_composition, list):
        return

    for comp_item in chemical_composition:
        if not isinstance(comp_item, dict):
            continue

        for list_key in ("chemicalCompositionMeasured", "chemicalCompositionNominal"):
            elements = comp_item.get(list_key)
            if not isinstance(elements, list):
                continue

            for elem in elements:
                if not isinstance(elem, dict):
                    continue
                if "measurementMethod" not in elem and isinstance(elem.get("method"), str):
                    if elem.get("method", "").strip():
                        elem["measurementMethod"] = elem["method"]


def normalize_experiment_data(schema_doc: dict, data_doc: dict):
    schema_properties = schema_doc.get("properties", {}) if isinstance(schema_doc, dict) else {}
    schema_target = schema_doc
    data_target = data_doc

    if isinstance(data_doc, dict) and "mappedMeasurementData" in data_doc:
        mapped = data_doc.get("mappedMeasurementData", {})
        if isinstance(mapped, dict) and "MeasurementData" in mapped:
            data_target = {"MeasurementData": mapped["MeasurementData"]}

    if isinstance(data_target, dict) and "MeasurementData" not in data_target and "MeasurementData" in schema_properties:
        # Accept both old camelCase keys (legacy) and new PascalCase keys (v2.1.2+).
        old_keys = {"additionalMetadata", "primaryData", "secondaryData"}
        new_keys = {"AdditionalMetadata", "PrimaryData", "SecondaryData"}
        if old_keys & data_target.keys() or new_keys & data_target.keys():
            data_target = {"MeasurementData": data_target}

    _normalize_legacy_chemical_composition_methods(data_target)

    return schema_target, data_target


def collect_required_paths(schema_root: dict, schema_node: dict, base_path=()):
    node = resolve_ref(schema_root, schema_node)
    paths = []

    required = node.get("required", []) if isinstance(node, dict) else []
    if isinstance(required, list):
        for key in required:
            if isinstance(key, str):
                paths.append(base_path + (key,))

    properties = node.get("properties", {}) if isinstance(node, dict) else {}
    if isinstance(properties, dict):
        for key, child in properties.items():
            if isinstance(child, dict):
                paths.extend(collect_required_paths(schema_root, child, base_path + (key,)))

    items = node.get("items") if isinstance(node, dict) else None
    if isinstance(items, dict):
        paths.extend(collect_required_paths(schema_root, items, base_path + ("*",)))

    # Only traverse allOf (all sub-schemas must apply).
    # oneOf/anyOf are mutually exclusive alternatives — collecting required
    # paths from every branch produces false positives (e.g. externalFileLink
    # flagged when element-by-element list form is used instead).
    for member in node.get("allOf", []) if isinstance(node, dict) else []:
        if isinstance(member, dict):
            paths.extend(collect_required_paths(schema_root, member, base_path))

    return paths


def check_path_defined(data_node, path_tuple):
    if not path_tuple:
        return True, data_node, None

    head, *tail = path_tuple
    if head == "*":
        if not isinstance(data_node, list):
            return False, None, "expected array for wildcard segment"
        if not data_node:
            return False, None, "array is empty"

        for idx, item in enumerate(data_node):
            ok, _, reason = check_path_defined(item, tuple(tail))
            if not ok:
                return False, None, f"array item {idx}: {reason}"
        return True, data_node, None

    if not isinstance(data_node, dict):
        return False, None, "parent is not an object"
    if head not in data_node:
        return False, None, "missing key"

    value = data_node[head]
    if not tail:
        return is_defined(value), value, "not defined" if not is_defined(value) else None

    return check_path_defined(value, tuple(tail))


def validate_required_keywords(schema_doc: dict, experiment_doc: dict):
    schema_target, data_target = normalize_experiment_data(schema_doc, experiment_doc)
    req_paths = list(dict.fromkeys(collect_required_paths(schema_target, schema_target)))

    warnings = []
    for req in req_paths:
        ok, _, reason = check_path_defined(data_target, req)
        if not ok:
            warnings.append({"path": ".".join(req), "reason": reason})

    return req_paths, warnings, schema_target, data_target


def run_jsonschema_validation(schema_target: dict, data_target, max_errors: int | None = None):
    from jsonschema import Draft201909Validator

    validator = Draft201909Validator(schema_target)
    errors = sorted(validator.iter_errors(data_target), key=lambda e: list(e.path))

    if isinstance(max_errors, int) and max_errors >= 0:
        errors = errors[:max_errors]

    normalized = []
    for err in errors:
        normalized.append(
            {
                "data_path": ".".join([str(p) for p in err.path]) if list(err.path) else "<root>",
                "message": str(err.message),
                "schema_path": "/".join([str(p) for p in err.schema_path]),
            }
        )
    return normalized


def infer_default_value(schema_root: dict, schema_node: dict):
    node = resolve_ref(schema_root, schema_node) if isinstance(schema_node, dict) else {}

    enum_values = node.get("enum", []) if isinstance(node, dict) else []
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    node_type = node.get("type") if isinstance(node, dict) else None
    if isinstance(node_type, list):
        ordered = ["object", "array", "string", "integer", "number", "boolean"]
        for item in ordered:
            if item in node_type:
                node_type = item
                break

    if node_type == "object" or isinstance(node.get("properties", {}), dict):
        props = node.get("properties", {}) if isinstance(node, dict) else {}
        if not isinstance(props, dict) or not props:
            return {}

        result = {}
        req = node.get("required", []) if isinstance(node, dict) else []
        if isinstance(req, list) and req:
            keys_to_fill = [k for k in req if isinstance(k, str) and k in props]
        elif "value" in props and "unit" in props:
            keys_to_fill = ["value", "unit"]
        else:
            keys_to_fill = [next(iter(props.keys()))]

        for key in keys_to_fill:
            result[key] = infer_default_value(schema_root, props[key])
        return result

    if node_type == "array":
        return []
    if node_type == "integer":
        return 0
    if node_type == "number":
        return 0.0
    if node_type == "boolean":
        return False
    return "TODO"


def autofix_required_fields(schema_root: dict, schema_node: dict, data_node):
    node = resolve_ref(schema_root, schema_node) if isinstance(schema_node, dict) else {}
    props = node.get("properties", {}) if isinstance(node, dict) else {}
    required = node.get("required", []) if isinstance(node, dict) else []
    changes = 0

    if isinstance(props, dict):
        if not isinstance(data_node, dict):
            data_node = {}
            changes += 1

        if isinstance(required, list):
            for key in required:
                if not isinstance(key, str):
                    continue
                child_schema = props.get(key, {})
                if key not in data_node or not is_defined(data_node.get(key)):
                    data_node[key] = infer_default_value(schema_root, child_schema)
                    changes += 1

        for key, child_schema in props.items():
            if key in data_node:
                fixed_child, child_changes = autofix_required_fields(schema_root, child_schema, data_node[key])
                data_node[key] = fixed_child
                changes += child_changes

    items_schema = node.get("items") if isinstance(node, dict) else None
    if isinstance(items_schema, dict) and isinstance(data_node, list):
        for idx, item in enumerate(data_node):
            fixed_child, child_changes = autofix_required_fields(schema_root, items_schema, item)
            data_node[idx] = fixed_child
            changes += child_changes

    return data_node, changes


def autofix_experiment_json(schema_doc: dict, experiment_doc: dict):
    fixed_doc = copy.deepcopy(experiment_doc)
    schema_target, data_target = normalize_experiment_data(schema_doc, fixed_doc)
    fixed_data_target, changes = autofix_required_fields(schema_target, schema_target, data_target)

    if isinstance(fixed_data_target, dict) and "MeasurementData" in fixed_data_target:
        if isinstance(fixed_doc, dict) and "mappedMeasurementData" in fixed_doc:
            mapped = fixed_doc.get("mappedMeasurementData", {})
            if isinstance(mapped, dict):
                mapped["MeasurementData"] = fixed_data_target["MeasurementData"]

    return fixed_doc, changes
