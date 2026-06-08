import argparse
import copy
import json
import os
import re
import sys
from html import escape
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for
from markupsafe import Markup
import validation_core
import shacl_validation_core


def extract_missing_required_key(error_obj) -> str | None:
    """Best-effort extraction of missing key from jsonschema 'required' errors."""
    params = getattr(error_obj, "params", None)
    if isinstance(params, dict):
        key = params.get("property") or params.get("required")
        if isinstance(key, str) and key:
            return key

    message = str(getattr(error_obj, "message", ""))
    if not message:
        return None

    parts = message.split("'")
    if len(parts) >= 2 and parts[1].strip():
        return parts[1].strip()

    parts = message.split('"')
    if len(parts) >= 2 and parts[1].strip():
        return parts[1].strip()

    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a small local web app for metadata validation.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8503, help="Port (default: 8503)")
    parser.add_argument(
        "--schema",
        default=os.path.join("..", "Data Schema", "2026-05_Data-Schema_Creep_v2.1.4.json"),
        help="Default schema JSON path",
    )
    parser.add_argument(
        "--data-root",
        default=os.path.join("Data"),
        help="Data root folder containing BAMDataset and BAMDataset_Json",
    )
    return parser.parse_args()


def list_json_files(folder_path: Path) -> list[Path]:
    if not folder_path.exists() or not folder_path.is_dir():
        return []
    return sorted([p for p in folder_path.rglob("*.json") if p.is_file()])


def list_lis_files(folder_path: Path) -> list[Path]:
    if not folder_path.exists() or not folder_path.is_dir():
        return []
    return sorted([p for p in folder_path.rglob("*.[Ll][Ii][Ss]") if p.is_file()])


def candidate_folders_with_pattern(data_root: Path, pattern: str) -> list[Path]:
    if not data_root.exists() or not data_root.is_dir():
        return []

    candidates = [data_root]
    candidates.extend([p for p in data_root.iterdir() if p.is_dir()])

    out = []
    for folder in candidates:
        has_match = any(folder.rglob(pattern))
        if has_match:
            out.append(folder)

    return sorted(dict.fromkeys(out))


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


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


def collect_required_paths(schema_root: dict, schema_node: dict, base_path=()) -> list[tuple[str, ...]]:
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
    # oneOf/anyOf represent mutually exclusive alternatives — collecting required
    # paths from every branch would flag missing fields that belong to the
    # unchosen alternative (e.g., externalFileLink vs element-by-element list).
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


def normalize_experiment_data(schema_doc: dict, data_doc: dict):
    schema_properties = schema_doc.get("properties", {}) if isinstance(schema_doc, dict) else {}
    schema_target = schema_doc
    data_target = data_doc

    if isinstance(data_doc, dict) and "mappedMeasurementData" in data_doc:
        mapped = data_doc.get("mappedMeasurementData", {})
        if isinstance(mapped, dict) and "MeasurementData" in mapped:
            data_target = {"MeasurementData": mapped["MeasurementData"]}

    if isinstance(data_target, dict) and "MeasurementData" not in data_target and "MeasurementData" in schema_properties:
        if "additionalMetadata" in data_target or "primaryData" in data_target or "secondaryData" in data_target:
            data_target = {"MeasurementData": data_target}

    return schema_target, data_target


def validate_required_keywords(schema_doc: dict, experiment_doc: dict):
    schema_target, data_target = normalize_experiment_data(schema_doc, experiment_doc)
    req_paths = list(dict.fromkeys(collect_required_paths(schema_target, schema_target)))

    warnings = []
    for req in req_paths:
        ok, _, reason = check_path_defined(data_target, req)
        if not ok:
            warnings.append({"path": ".".join(req), "reason": reason})

    return req_paths, warnings, schema_target, data_target


def infer_default_value(schema_root: dict, schema_node: dict):
    node = resolve_ref(schema_root, schema_node) if isinstance(schema_node, dict) else {}

    enum_values = node.get("enum", []) if isinstance(node, dict) else []
    if isinstance(enum_values, list) and enum_values:
        return enum_values[0]

    node_type = node.get("type") if isinstance(node, dict) else None
    if isinstance(node_type, list):
        ordered = ["object", "array", "string", "integer", "number", "boolean"]
        for t in ordered:
            if t in node_type:
                node_type = t
                break

    if node_type == "object" or isinstance(node.get("properties", {}), dict):
        props = node.get("properties", {}) if isinstance(node, dict) else {}
        if not isinstance(props, dict) or not props:
            return {}

        result = {}
        req = node.get("required", []) if isinstance(node, dict) else []
        keys_to_fill = []
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

    # Keep normalized wrapper in sync in case root replacement happened.
    if isinstance(fixed_data_target, dict) and "MeasurementData" in fixed_data_target:
        if isinstance(fixed_doc, dict) and "mappedMeasurementData" in fixed_doc:
            mapped = fixed_doc.get("mappedMeasurementData", {})
            if isinstance(mapped, dict):
                mapped["MeasurementData"] = fixed_data_target["MeasurementData"]

    return fixed_doc, changes


def path_to_dom_id(path: str) -> str:
    normalized = path.strip()
    if not normalized:
        return "field-root"
    safe = re.sub(r"[^0-9A-Za-z_-]+", "-", normalized)
    safe = re.sub(r"-+", "-", safe).strip("-")
    if not safe:
        safe = "field"
    return f"field-{safe}"


def _set_by_path(root_obj, path_parts, value):
    if not path_parts:
        return value

    cur = root_obj
    for i, part in enumerate(path_parts):
        is_last = i == len(path_parts) - 1

        if isinstance(part, int):
            if not isinstance(cur, list):
                return root_obj
            while len(cur) <= part:
                cur.append({})
            if is_last:
                cur[part] = value
                return root_obj
            cur = cur[part]
        else:
            if not isinstance(cur, dict):
                return root_obj
            if is_last:
                cur[part] = value
                return root_obj
            if part not in cur or cur[part] is None:
                next_part = path_parts[i + 1]
                cur[part] = [] if isinstance(next_part, int) else {}
            cur = cur[part]

    return root_obj


def _get_by_path(root_obj, path_parts):
    cur = root_obj
    for part in path_parts:
        if isinstance(part, int):
            if not isinstance(cur, list) or part >= len(cur):
                return None
            cur = cur[part]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return None
            cur = cur[part]
    return cur


def autofix_schema_errors(schema_target: dict, data_target):
    try:
        from jsonschema import Draft201909Validator
    except ImportError:
        return data_target, 0

    validator = Draft201909Validator(schema_target)
    total_changes = 0

    # A few passes usually resolve cascaded errors.
    for _ in range(5):
        errors = sorted(validator.iter_errors(data_target), key=lambda e: list(e.path))
        if not errors:
            break

        changed_this_round = 0
        for err in errors:
            path_parts = list(err.path)

            if err.validator == "required":
                missing = extract_missing_required_key(err)
                if missing and isinstance(err.instance, dict):
                    parent_schema = err.schema if isinstance(err.schema, dict) else {}
                    child_schema = parent_schema.get("properties", {}).get(missing, {}) if isinstance(parent_schema.get("properties", {}), dict) else {}
                    err.instance[missing] = infer_default_value(schema_target, child_schema)
                    changed_this_round += 1
                continue

            if err.validator == "type":
                replacement = infer_default_value(schema_target, err.schema if isinstance(err.schema, dict) else {})
                _set_by_path(data_target, path_parts, replacement)
                changed_this_round += 1
                continue

            if err.validator == "enum":
                enum_vals = err.validator_value if isinstance(err.validator_value, list) else []
                if enum_vals:
                    _set_by_path(data_target, path_parts, enum_vals[0])
                    changed_this_round += 1
                continue

            # Handle arrays that must contain at least one item.
            if err.validator == "minItems":
                cur_val = _get_by_path(data_target, path_parts)
                if isinstance(cur_val, list) and not cur_val:
                    item_schema = err.schema.get("items", {}) if isinstance(err.schema, dict) else {}
                    cur_val.append(infer_default_value(schema_target, item_schema))
                    changed_this_round += 1
                continue

        total_changes += changed_this_round
        if changed_this_round == 0:
            break

    return data_target, total_changes


def convert_lis_to_json(project_root: Path, lis_path: Path, output_json_path: Path, mapping_path: Path):
    import importlib
    import subprocess

    if not lis_path.exists():
        raise FileNotFoundError(f"LIS file not found: {lis_path}")

    output_json_path.parent.mkdir(parents=True, exist_ok=True)

    # Newest dataset files use the hierarchical v2 LIS format and must go
    # through the v2 translator stack (ParserV2 + BAM2schema_v2 mapping).
    is_v2_lis = False
    for enc in ("latin1", "utf-8"):
        try:
            with lis_path.open("r", encoding=enc) as handle:
                for _ in range(15):
                    line = handle.readline()
                    if not line:
                        break
                    if line.strip().startswith("CATEGORIZATION"):
                        is_v2_lis = True
                        break
            if is_v2_lis:
                break
        except UnicodeDecodeError:
            continue

    if is_v2_lis:
        v2_script = project_root / "bin" / "translate_bam_data_v2.py"
        if not v2_script.exists():
            raise FileNotFoundError(f"v2 translator script not found: {v2_script}")

        v2_mapping = project_root / "Metadata" / "Mappings" / "BAM2schema_v2.json"
        cmd = [
            sys.executable,
            str(v2_script),
            str(lis_path),
            "--output",
            str(output_json_path),
        ]
        if v2_mapping.exists():
            cmd.extend(["--mapping", str(v2_mapping)])

        proc = subprocess.run(cmd, cwd=str(project_root), capture_output=True, text=True)
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            raise RuntimeError(detail or f"v2 translation failed (exit code {proc.returncode})")

        return output_json_path

    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    lis_pkg_root = project_root / "dependencies" / "LISParser"
    mappings_pkg_root = project_root / "dependencies" / "Mappingsreader"
    for p in [lis_pkg_root, mappings_pkg_root]:
        p_txt = str(p)
        if p.exists() and p_txt not in sys.path:
            sys.path.insert(0, p_txt)

    parser_mod = importlib.import_module("LISParser.LisParse")
    map_mod = importlib.import_module("mappingsreader.mapreader")

    Parser = getattr(parser_mod, "Parser")
    translate_bam = getattr(map_mod, "translate_bam")

    mapping_document = load_json(mapping_path)
    lis_dict = Parser(str(lis_path)).parse_lis()
    metadata = lis_dict.get("metadata", {}) if isinstance(lis_dict, dict) else {}
    translated = translate_bam(metadata, mapping_document)

    with output_json_path.open("w", encoding="utf-8") as f:
        json.dump(translated, f, indent=4, ensure_ascii=False)

    return output_json_path


def tree_html_from_schema(schema_root: dict, schema_node: dict, data_node, base_path=(), show_validation: bool = True):
    def _resolve_for_render(node_candidate: dict, current_data):
        node_local = resolve_ref(schema_root, node_candidate) if isinstance(node_candidate, dict) else {}

        # Choose a compatible branch when combiners are used (common for oneOf).
        for combiner in ("oneOf", "anyOf"):
            members = node_local.get(combiner, []) if isinstance(node_local, dict) else []
            if isinstance(members, list) and members:
                for member in members:
                    resolved_member = resolve_ref(schema_root, member) if isinstance(member, dict) else {}
                    member_type = resolved_member.get("type") if isinstance(resolved_member, dict) else None
                    if isinstance(current_data, list) and (member_type == "array" or "items" in resolved_member):
                        return resolved_member
                    if isinstance(current_data, dict) and (member_type == "object" or isinstance(resolved_member.get("properties"), dict)):
                        return resolved_member
                first_member = members[0]
                return resolve_ref(schema_root, first_member) if isinstance(first_member, dict) else node_local

        if isinstance(node_local, dict) and "allOf" in node_local:
            members = node_local.get("allOf", [])
            if isinstance(members, list) and members:
                # Merge allOf members for rendering so composite objects expose
                # all fields (e.g., element + value + unit).
                # Seed with the parent node's own properties/required/type so
                # they are not lost when allOf members are purely if/then conditionals
                # (e.g. TestPiece which has properties + an allOf conditional).
                merged = {
                    "properties": dict(node_local.get("properties", {})),
                    "required": list(node_local.get("required", [])),
                }
                merged_type = node_local.get("type")

                for member in members:
                    if not isinstance(member, dict):
                        continue
                    resolved_member = resolve_ref(schema_root, member)
                    if not isinstance(resolved_member, dict):
                        continue

                    member_type = resolved_member.get("type")
                    if isinstance(member_type, str) and merged_type is None:
                        merged_type = member_type

                    member_props = resolved_member.get("properties", {})
                    if isinstance(member_props, dict):
                        merged["properties"].update(member_props)

                    member_required = resolved_member.get("required", [])
                    if isinstance(member_required, list):
                        for req_key in member_required:
                            if isinstance(req_key, str) and req_key not in merged["required"]:
                                merged["required"].append(req_key)

                if merged_type is not None:
                    merged["type"] = merged_type

                if merged["properties"]:
                    return merged

                first_member = members[0]
                if isinstance(first_member, dict):
                    return resolve_ref(schema_root, first_member)

        return node_local

    node = _resolve_for_render(schema_node, data_node)

    # Render arrays using their item schema for a structured expandable view.
    items_schema = node.get("items") if isinstance(node, dict) else None
    is_array_node = isinstance(node, dict) and (node.get("type") == "array" or isinstance(items_schema, dict))
    if is_array_node:
        if not isinstance(data_node, list):
            if data_node is None:
                return "<span style='color:#999;'>(not provided)</span>"
            return escape(str(data_node))

        if len(data_node) == 0:
            return "<span style='color:#a00;font-weight:600;'>(empty array)</span>"

        # Readability tweak: for single-entry arrays, render the item directly
        # instead of showing a synthetic [0] layer.
        if len(data_node) == 1:
            return tree_html_from_schema(
                schema_root,
                items_schema if isinstance(items_schema, dict) else {},
                data_node[0],
                base_path,
                show_validation=show_validation,
            )

        html_parts = ["<ul style='list-style-type:none;padding-left:18px;margin:4px 0;'>"]
        for idx, item in enumerate(data_node):
            item_path = base_path + (str(idx),)
            item_path_str = ".".join(item_path)
            anchor_id = path_to_dom_id(item_path_str)
            rendered_item = tree_html_from_schema(
                schema_root,
                items_schema if isinstance(items_schema, dict) else {},
                item,
                item_path,
                show_validation=show_validation,
            )
            html_parts.append(
                "<li>"
                f"<details><summary><span id='{escape(anchor_id)}' style='color:#1f2937;font-weight:600;'>[{idx}]</span></summary>"
                f"{rendered_item}"
                "</details>"
                "</li>"
            )
        html_parts.append("</ul>")
        return "".join(html_parts)

    props = node.get("properties", {}) if isinstance(node, dict) else {}

    if not isinstance(props, dict) or not props:
        if isinstance(data_node, dict):
            return ""
        if isinstance(data_node, list):
            return escape(json.dumps(data_node, ensure_ascii=False))
        if data_node is None or (isinstance(data_node, str) and data_node.strip() == ""):
            return "<span style='color:#a00;font-weight:600;'>(empty)</span>"
        return escape(str(data_node))

    html_parts = ["<ul style='list-style-type:none;padding-left:18px;margin:4px 0;'>"]
    required_set = set(node.get("required", [])) if isinstance(node, dict) else set()

    for key, child_schema in props.items():
        current_path = base_path + (key,)
        current_path_str = ".".join(current_path)
        anchor_id = path_to_dom_id(current_path_str)
        required_here = key in required_set
        present = isinstance(data_node, dict) and key in data_node
        value = data_node.get(key) if isinstance(data_node, dict) and key in data_node else None

        missing_or_empty = show_validation and required_here and (not present or not is_defined(value))
        key_style = "color:#a00;font-weight:700;" if missing_or_empty else "color:#1f2937;font-weight:600;"
        req_tag = ""
        if show_validation:
            req_tag = (
                " <span style='color:#a00;'>(required, missing)</span>"
                if missing_or_empty
                else (" <span style='color:#0a7a2a;'>(required)</span>" if required_here else "")
            )

        child_node = _resolve_for_render(child_schema, value)
        child_props = child_node.get("properties", {}) if isinstance(child_node, dict) else {}
        child_items = child_node.get("items") if isinstance(child_node, dict) else None
        is_branch = (
            (isinstance(child_props, dict) and len(child_props) > 0)
            or child_node.get("type") == "array"
            or isinstance(child_items, dict)
            or "oneOf" in child_node
            or "anyOf" in child_node
            or "allOf" in child_node
        ) if isinstance(child_node, dict) else False

        # Dropdown shortcut: if the value is a dict produced by a dropdown schema
        # (single "*Options" key), render only the selected string — not the raw object.
        # When "Other" is selected, render the companion other* field value instead.
        if isinstance(value, dict) and value:
            _opt_keys = [_k for _k in value if _k.endswith("Options")]
            if len(_opt_keys) == 1:
                _selected = value[_opt_keys[0]]
                if isinstance(_selected, str):
                    # When "Other (Please specify...)" is chosen, show the actual
                    # value stored in the companion other* sibling field.
                    if _selected.startswith("Other"):
                        _base = _opt_keys[0][:-len("Options")]  # e.g. "calibrationStandard"
                        _other_key = "other" + _base[0].upper() + _base[1:]  # e.g. "otherCalibrationStandard"
                        _other_val = value.get(_other_key, "")
                        _display = _other_val if _other_val else _selected
                    else:
                        _display = _selected
                    _rval = escape(_display) if _display.strip() else "<span style='color:#a00;font-weight:600;'>(empty)</span>"
                    html_parts.append(
                        "<li>"
                        f"<span id='{escape(anchor_id)}' style='{key_style}'>{escape(key)}</span>{req_tag}: "
                        f"<span>{_rval}</span>"
                        "</li>"
                    )
                    continue

        if is_branch:
            html_parts.append(
                "<li>"
                f"<details open><summary><span id='{escape(anchor_id)}' style='{key_style}'>{escape(key)}</span>{req_tag}</summary>"
                f"{tree_html_from_schema(schema_root, child_schema, value if isinstance(value, (dict, list)) else {}, current_path, show_validation=show_validation)}"
                "</details>"
                "</li>"
            )
        else:
            if not present:
                rendered_val = "<span style='color:#999;'>(not provided)</span>"
            elif value is None or (isinstance(value, str) and value.strip() == ""):
                rendered_val = "<span style='color:#a00;font-weight:600;'>(empty)</span>"
            elif isinstance(value, (dict, list)):
                rendered_val = escape(json.dumps(value, ensure_ascii=False))
            else:
                rendered_val = escape(str(value))

            html_parts.append(
                "<li>"
                f"<span id='{escape(anchor_id)}' style='{key_style}'>{escape(key)}</span>{req_tag}: "
                f"<span>{rendered_val}</span>"
                "</li>"
            )

    html_parts.append("</ul>")
    return "".join(html_parts)


def create_app(default_schema: str, data_root_value: str) -> Flask:
    app = Flask(__name__)

    root_dir = Path(__file__).resolve().parents[1]
    data_root = (root_dir / data_root_value).resolve()
    default_schema_path = (root_dir / default_schema).resolve()
    default_json_folder = (data_root / "BAMDataset_Json").resolve()
    default_lis_folder = (data_root / "BAMDataset").resolve()
    schema_root = (root_dir / ".." / "Data Schema").resolve()
    default_mapping = (root_dir / "Metadata" / "Mappings" / "BAM2schema.json").resolve()

    state = {
        "schema_path": str(default_schema_path),
        "json_folder": str(default_json_folder),
        "json_file": "",
        "lis_folder": str(default_lis_folder),
        "lis_file": "",
        "shacl_data_graph": str((root_dir / "shacl_validation" / "rdfGraph_smallExample.ttl").resolve()),
        "shacl_shapes_graph": str((root_dir / "shacl_validation" / "shaclShape_smallExample.ttl").resolve()),
        "output_name": "selected_from_lis_translated.json",
        "message": "",
        "error": "",
        "required_warnings": [],
        "required_count": 0,
        "tree_html": "",
        "displayed_json_file": "",
        "validation_ran": False,
        "schema_errors": [],
        "shacl_conforms": None,
        "shacl_report_text": "",
        "validated_file": "",
        "fixed_json_path": "",
        "fixed_json_preview": "",
    }

    def suggested_output_name_from_lis(lis_file: str) -> str:
        if not lis_file:
            return "selected_from_lis_translated.json"
        stem = Path(lis_file).stem
        return f"{stem}_translated.json"

    template = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>IUC02 Metadata Validation Web App</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; max-width: 1250px; }
    h1, h2 { margin-bottom: 8px; }
    .panel { border: 1px solid #ddd; padding: 12px; margin: 12px 0; border-radius: 8px; }
    .row { margin-bottom: 10px; }
    label { display: block; margin-bottom: 4px; font-weight: 600; }
    input[type="text"], select { width: 100%; padding: 7px; }
    button { padding: 8px 14px; margin-right: 8px; }
    .ok { color: #0a7a2a; margin: 8px 0; }
    .error { color: #b00020; margin: 8px 0; }
    table { border-collapse: collapse; width: 100%; font-size: 13px; }
    th, td { border: 1px solid #ddd; padding: 6px; text-align: left; vertical-align: top; }
    th { background: #f7f7f7; }
    .split { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
    @media (max-width: 900px) { .split { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <h1>IUC02 Metadata Validation</h1>

  <form method="post" action="{{ url_for('action') }}" class="panel">
    <h2>Inputs</h2>
        <div class="row">
            <label>Schema file selection</label>
            <select id="schema_select" onchange="setSchemaPathAndSubmit(this.value)">
                {% for label, value in schema_options %}
                <option value="{{ value }}" {% if value == schema_path %}selected{% endif %}>{{ label }}</option>
                {% endfor %}
            </select>
        </div>
    <div class="row">
      <label>Schema file path</label>
            <input id="schema_path" type="text" name="schema_path" value="{{ schema_path }}" />
    </div>

    <div class="split">
      <div>
        <h3>JSON Selection</h3>
        <div class="row">
          <label>JSON Folder</label>
                    <select name="json_folder" onchange="this.form.submit()">
            {% for label, value in json_folder_options %}
            <option value="{{ value }}" {% if value == json_folder %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="row">
          <label>Experiment JSON</label>
          <select name="json_file">
            {% for label, value in json_file_options %}
            <option value="{{ value }}" {% if value == json_file %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        <button type="submit" name="action" value="refresh_json">Refresh JSON Lists</button>
                <button type="submit" name="action" value="autofix_json">Auto-fix JSON</button>
      </div>

      <div>
        <h3>LIS to JSON</h3>
        <div class="row">
          <label>LIS Folder</label>
                    <select name="lis_folder" onchange="this.form.submit()">
            {% for label, value in lis_folder_options %}
            <option value="{{ value }}" {% if value == lis_folder %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="row">
          <label>LIS File</label>
                                        <select id="lis_file" name="lis_file" onchange="this.form.submit()">
            {% for label, value in lis_file_options %}
            <option value="{{ value }}" {% if value == lis_file %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="row">
          <label>Output JSON filename</label>
                    <input id="output_name" type="text" name="output_name" value="{{ output_name }}" />
        </div>
        <button type="submit" name="action" value="convert_lis">Convert LIS to JSON</button>
      </div>
    </div>

    <div class="row" style="margin-top:12px;">
      <button type="submit" name="action" value="validate">Run Validation</button>
            <button type="submit" name="action" value="autofix_json">Auto-fix JSON</button>
    </div>
  </form>

    <form method="post" action="{{ url_for('action') }}" class="panel">
        <h2>RDF + SHACL Validation</h2>
        <div class="row">
            <label>Data graph path (RDF)</label>
            <input type="text" name="shacl_data_graph" value="{{ shacl_data_graph }}" />
        </div>
        <div class="row">
            <label>SHACL shapes path</label>
            <input type="text" name="shacl_shapes_graph" value="{{ shacl_shapes_graph }}" />
        </div>
        <button type="submit" name="action" value="validate_shacl">Run SHACL Validation</button>
    </form>

  {% if message %}<p class="ok">{{ message }}</p>{% endif %}
  {% if error %}<p class="error">{{ error }}</p>{% endif %}

    {% if displayed_json_file %}
  <div class="panel">
                <h2>JSON Render</h2>
        <p><b>File:</b> {{ displayed_json_file }}</p>
        {% if validation_ran %}
        <h3>Validation Summary</h3>
    <p><b>Total required keywords declared:</b> {{ required_count }}</p>
    {% if required_warnings|length == 0 %}
      <p class="ok">All required keywords are defined.</p>
    {% else %}
      <p class="error">Missing or undefined required keywords: {{ required_warnings|length }}</p>
            <details open>
                <summary><b>Missing required field list</b></summary>
                <ul>
                    {% for warning in required_warnings %}
                        <li>
                            <a href="#{{ warning.anchor }}">{{ warning.path }}</a>
                            {% if warning.reason %} ({{ warning.reason }}){% endif %}
                        </li>
                    {% endfor %}
                </ul>
            </details>
    {% endif %}
    {% else %}
      <p>Preview of the current JSON. Run validation to add required-field tags to this render.</p>
    {% endif %}

        <h2>Tree View</h2>
        {% if validation_ran %}
        <div>
            <span style="color:#0a7a2a;font-weight:600;">(required)</span> = required and defined,
            <span style="color:#a00;font-weight:700;">(required, missing)</span> = required but missing/empty.
        </div>
        {% endif %}
        <div>{{ tree_html|safe }}</div>
  </div>
  {% endif %}

    {% if fixed_json_path %}
    <div class="panel">
        <h2>Fixed JSON</h2>
        <p><b>Saved file:</b> {{ fixed_json_path }}</p>
        <details open>
            <summary>Show fixed JSON content</summary>
            <pre style="white-space:pre-wrap;background:#fafafa;border:1px solid #ddd;padding:10px;max-height:420px;overflow:auto;">{{ fixed_json_preview }}</pre>
        </details>
    </div>
    {% endif %}

        {% if shacl_conforms is not none %}
        <div class="panel">
            <h2>SHACL Validation Summary</h2>
            {% if shacl_conforms %}
                <p class="ok">RDF graph conforms to SHACL shapes.</p>
            {% else %}
                <p class="error">RDF graph does not conform to SHACL shapes.</p>
            {% endif %}
            <details open>
                <summary>Show SHACL report</summary>
                <pre style="white-space:pre-wrap;background:#fafafa;border:1px solid #ddd;padding:10px;max-height:420px;overflow:auto;">{{ shacl_report_text }}</pre>
            </details>
        </div>
        {% endif %}

<script>
    function setSchemaPathAndSubmit(schemaPath) {
        const input = document.getElementById("schema_path");
        if (!input) return;
        input.value = schemaPath || "";
        if (input.form) {
            input.form.submit();
        }
    }

    function setOutputNameFromLis(lisPath) {
        const outputInput = document.getElementById("output_name");
        if (!outputInput) return;
        const filename = (lisPath || "").split(/[/\\]/).pop();
        if (!filename) return;
        const stem = filename.replace(/\.[^.]+$/i, "");
        outputInput.value = stem + "_translated.json";
    }

    document.addEventListener("DOMContentLoaded", function () {
        const lisSelect = document.getElementById("lis_file");
        if (!lisSelect) return;
        setOutputNameFromLis(lisSelect.value);
    });
</script>
</body>
</html>
    """

    def build_folder_file_options():
        json_folders = candidate_folders_with_pattern(data_root, "*.json")
        lis_folders = candidate_folders_with_pattern(data_root, "*.LIS")

        if not json_folders:
            json_folder_options = [("(no folders with JSON)", "")]
            json_files = []
            state["json_folder"] = ""
            state["json_file"] = ""
        else:
            if state["json_folder"] not in [str(p) for p in json_folders]:
                state["json_folder"] = str(default_json_folder if default_json_folder in json_folders else json_folders[0])
            json_folder_options = [(str(p.relative_to(root_dir)), str(p)) for p in json_folders]
            json_files = list_json_files(Path(state["json_folder"]))

        if json_files:
            if state["json_file"] not in [str(p) for p in json_files]:
                state["json_file"] = str(json_files[0])
            json_file_options = [(str(p.relative_to(Path(state["json_folder"]))), str(p)) for p in json_files]
        else:
            state["json_file"] = ""
            json_file_options = [("(no JSON files)", "")]

        if not lis_folders:
            lis_folder_options = [("(no folders with LIS)", "")]
            lis_files = []
            state["lis_folder"] = ""
            state["lis_file"] = ""
        else:
            if state["lis_folder"] not in [str(p) for p in lis_folders]:
                state["lis_folder"] = str(default_lis_folder if default_lis_folder in lis_folders else lis_folders[0])
            lis_folder_options = [(str(p.relative_to(root_dir)), str(p)) for p in lis_folders]
            lis_files = list_lis_files(Path(state["lis_folder"]))

        if lis_files:
            if state["lis_file"] not in [str(p) for p in lis_files]:
                state["lis_file"] = str(lis_files[0])
            lis_file_options = [(str(p.relative_to(Path(state["lis_folder"]))), str(p)) for p in lis_files]
        else:
            state["lis_file"] = ""
            lis_file_options = [("(no LIS files)", "")]

        return json_folder_options, json_file_options, lis_folder_options, lis_file_options

    def build_schema_options():
        if not schema_root.exists() or not schema_root.is_dir():
            return [(state["schema_path"], state["schema_path"])]

        schema_files = sorted([p for p in schema_root.glob("*.json") if p.is_file()])
        options = [(str(p.relative_to(root_dir.parent)), str(p)) for p in schema_files]

        if state["schema_path"] not in [value for _, value in options]:
            options.insert(0, (f"(custom) {state['schema_path']}", state["schema_path"]))

        return options or [(state["schema_path"], state["schema_path"])]

    def clear_validation_state():
        state["required_warnings"] = []
        state["required_count"] = 0
        state["schema_errors"] = []
        state["validated_file"] = ""
        state["validation_ran"] = False

    def render_json_file(json_file: Path, *, show_validation: bool) -> None:
        schema_path = Path(state["schema_path"])

        if not schema_path.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_path}")
        if not json_file.exists():
            raise FileNotFoundError(f"JSON file not found: {json_file}")

        schema_doc = validation_core.load_json(schema_path)
        experiment_doc = validation_core.load_json(json_file)

        if show_validation:
            req_paths, warnings, schema_target, data_target = validation_core.validate_required_keywords(schema_doc, experiment_doc)
            state["required_warnings"] = [
                {
                    "path": warning.get("path", ""),
                    "reason": warning.get("reason", ""),
                    "anchor": path_to_dom_id(warning.get("path", "")),
                }
                for warning in warnings
            ]
            state["required_count"] = len(req_paths)
            state["schema_errors"] = validation_core.run_jsonschema_validation(
                schema_target,
                data_target,
                max_errors=200,
            )
            state["validated_file"] = str(json_file)
            state["validation_ran"] = True
        else:
            schema_target, data_target = validation_core.normalize_experiment_data(schema_doc, experiment_doc)
            clear_validation_state()

        state["displayed_json_file"] = str(json_file)
        state["tree_html"] = tree_html_from_schema(
            schema_target,
            schema_target,
            data_target,
            show_validation=show_validation,
        )

    def render_home():
        json_folder_options, json_file_options, lis_folder_options, lis_file_options = build_folder_file_options()
        schema_options = build_schema_options()
        return render_template_string(
            template,
            schema_path=state["schema_path"],
            schema_options=schema_options,
            json_folder=state["json_folder"],
            json_file=state["json_file"],
            lis_folder=state["lis_folder"],
            lis_file=state["lis_file"],
            shacl_data_graph=state["shacl_data_graph"],
            shacl_shapes_graph=state["shacl_shapes_graph"],
            output_name=state["output_name"],
            message=state["message"],
            error=state["error"],
            required_warnings=state["required_warnings"],
            required_count=state["required_count"],
            tree_html=Markup(state["tree_html"]),
            displayed_json_file=state["displayed_json_file"],
            validation_ran=state["validation_ran"],
            schema_errors=state["schema_errors"],
            shacl_conforms=state["shacl_conforms"],
            shacl_report_text=state["shacl_report_text"],
            validated_file=state["validated_file"],
            fixed_json_path=state["fixed_json_path"],
            fixed_json_preview=state["fixed_json_preview"],
            json_folder_options=json_folder_options,
            json_file_options=json_file_options,
            lis_folder_options=lis_folder_options,
            lis_file_options=lis_file_options,
        )

    @app.get("/")
    def home():
        return render_home()

    @app.post("/action")
    def action():
        prev_lis_file = state["lis_file"]
        state["schema_path"] = request.form.get("schema_path", state["schema_path"]).strip()
        state["json_folder"] = request.form.get("json_folder", state["json_folder"]).strip()
        state["json_file"] = request.form.get("json_file", state["json_file"]).strip()
        state["lis_folder"] = request.form.get("lis_folder", state["lis_folder"]).strip()
        state["lis_file"] = request.form.get("lis_file", state["lis_file"]).strip()
        state["shacl_data_graph"] = request.form.get("shacl_data_graph", state["shacl_data_graph"]).strip()
        state["shacl_shapes_graph"] = request.form.get("shacl_shapes_graph", state["shacl_shapes_graph"]).strip()
        posted_output_name = request.form.get("output_name", state["output_name"]).strip()
        selected_action = request.form.get("action", "")
        if state["lis_file"] and (state["lis_file"] != prev_lis_file or selected_action in {"", "refresh_json", "convert_lis"}):
            state["output_name"] = suggested_output_name_from_lis(state["lis_file"])
        else:
            state["output_name"] = posted_output_name

        state["message"] = ""
        state["error"] = ""

        if selected_action != "autofix_json":
            state["fixed_json_path"] = ""
            state["fixed_json_preview"] = ""

        if selected_action != "validate_shacl":
            state["shacl_conforms"] = None
            state["shacl_report_text"] = ""

        if selected_action in {"refresh_json", "", "convert_lis", "autofix_json"}:
            clear_validation_state()

        if selected_action == "convert_lis":
            try:
                if not state["lis_file"]:
                    raise ValueError("Select a LIS file first.")
                if not state["json_folder"]:
                    raise ValueError("Select a JSON output folder first.")

                output_name = state["output_name"] or "selected_from_lis_translated.json"
                if not output_name.lower().endswith(".json"):
                    output_name = f"{output_name}.json"

                output_json_path = Path(state["json_folder"]) / output_name
                converted = convert_lis_to_json(
                    root_dir,
                    Path(state["lis_file"]),
                    output_json_path,
                    default_mapping,
                )
                state["json_file"] = str(converted)
                render_json_file(converted, show_validation=False)
                state["message"] = f"LIS converted successfully: {converted}"
            except Exception as exc:
                state["error"] = f"LIS conversion failed: {exc}"

            return redirect(url_for("home"))

        if selected_action == "autofix_json":
            try:
                schema_path = Path(state["schema_path"])
                json_file = Path(state["json_file"]) if state["json_file"] else None

                if not schema_path.exists():
                    raise FileNotFoundError(f"Schema file not found: {schema_path}")
                if json_file is None or not json_file.exists():
                    raise FileNotFoundError("Select a valid JSON experiment file.")

                schema_doc = validation_core.load_json(schema_path)
                experiment_doc = validation_core.load_json(json_file)

                fixed_doc, changes = validation_core.autofix_experiment_json(schema_doc, experiment_doc)

                # Second pass: repair common schema errors directly from validator feedback.
                schema_target, data_target = validation_core.normalize_experiment_data(schema_doc, fixed_doc)
                fixed_data_target, schema_fix_changes = autofix_schema_errors(schema_target, data_target)
                changes += schema_fix_changes

                # Keep normalized wrapper in sync in case schema-fix changed it.
                if isinstance(fixed_data_target, dict) and "MeasurementData" in fixed_data_target:
                    if isinstance(fixed_doc, dict) and "mappedMeasurementData" in fixed_doc:
                        mapped = fixed_doc.get("mappedMeasurementData", {})
                        if isinstance(mapped, dict):
                            mapped["MeasurementData"] = fixed_data_target["MeasurementData"]

                # Prefer naming from selected LIS input when available.
                if state.get("lis_file"):
                    lis_name = Path(state["lis_file"]).stem
                    fixed_name = f"{lis_name}_fixed.json"
                else:
                    fixed_name = f"{json_file.stem}_fixed{json_file.suffix}"

                fixed_path = Path(state["json_folder"]) / fixed_name
                with fixed_path.open("w", encoding="utf-8") as f:
                    json.dump(fixed_doc, f, indent=4, ensure_ascii=False)

                state["json_file"] = str(fixed_path)
                render_json_file(fixed_path, show_validation=False)
                state["message"] = f"Auto-fix finished: {changes} update(s). Saved to {fixed_path}"
                state["fixed_json_path"] = str(fixed_path)
                state["fixed_json_preview"] = json.dumps(fixed_doc, indent=2, ensure_ascii=False)
            except Exception as exc:
                state["error"] = f"Auto-fix failed: {exc}"

            return redirect(url_for("home"))

        if selected_action == "validate":
            try:
                schema_path = Path(state["schema_path"])
                json_file = Path(state["json_file"]) if state["json_file"] else None

                if not schema_path.exists():
                    raise FileNotFoundError(f"Schema file not found: {schema_path}")
                if json_file is None or not json_file.exists():
                    raise FileNotFoundError("Select a valid JSON experiment file.")

                render_json_file(json_file, show_validation=True)
                state["message"] = "Validation completed."
            except Exception as exc:
                state["error"] = f"Validation failed: {exc}"

            return redirect(url_for("home"))

        if selected_action == "validate_shacl":
            try:
                data_graph = Path(state["shacl_data_graph"])
                shacl_shapes = Path(state["shacl_shapes_graph"])
                report = shacl_validation_core.run_shacl_validation(
                    data_graph_path=data_graph,
                    shacl_shapes_path=shacl_shapes,
                    data_graph_format="turtle",
                    shacl_graph_format="turtle",
                )

                state["shacl_conforms"] = report["conforms"]
                state["shacl_report_text"] = report["report_text"]
                state["message"] = "SHACL validation completed."
            except Exception as exc:
                state["error"] = f"SHACL validation failed: {exc}"

            return redirect(url_for("home"))

        # refresh_json or default action: just re-render with current state
        return redirect(url_for("home"))

    return app


def main() -> None:
    args = parse_args()
    app = create_app(args.schema, args.data_root)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
