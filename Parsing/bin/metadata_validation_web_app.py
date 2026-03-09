import argparse
import copy
import json
import os
import sys
from html import escape
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for
from markupsafe import Markup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Serve a small local web app for metadata validation.")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8503, help="Port (default: 8503)")
    parser.add_argument(
        "--schema",
        default=os.path.join("..", "Data Schema", "2024-09_Schema_IUC02_v1.1.json"),
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
    return sorted([p for p in folder_path.rglob("*.LIS") if p.is_file()])


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

    for combiner in ("allOf", "anyOf", "oneOf"):
        members = node.get(combiner, []) if isinstance(node, dict) else []
        if isinstance(members, list):
            for member in members:
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
                missing = err.message.split("'")[1] if "'" in err.message else None
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

    if not lis_path.exists():
        raise FileNotFoundError(f"LIS file not found: {lis_path}")
    if not mapping_path.exists():
        raise FileNotFoundError(f"Mapping file not found: {mapping_path}")

    output_json_path.parent.mkdir(parents=True, exist_ok=True)

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


def tree_html_from_schema(schema_root: dict, schema_node: dict, data_node):
    node = resolve_ref(schema_root, schema_node) if isinstance(schema_node, dict) else {}
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
        required_here = key in required_set
        present = isinstance(data_node, dict) and key in data_node
        value = data_node.get(key) if isinstance(data_node, dict) and key in data_node else None

        missing_or_empty = required_here and (not present or not is_defined(value))
        key_style = "color:#a00;font-weight:700;" if missing_or_empty else "color:#1f2937;font-weight:600;"
        req_tag = (
            " <span style='color:#a00;'>(required, missing)</span>"
            if missing_or_empty
            else (" <span style='color:#0a7a2a;'>(required)</span>" if required_here else "")
        )

        child_node = resolve_ref(schema_root, child_schema) if isinstance(child_schema, dict) else {}
        child_props = child_node.get("properties", {}) if isinstance(child_node, dict) else {}
        is_branch = isinstance(child_props, dict) and len(child_props) > 0

        if is_branch:
            html_parts.append(
                "<li>"
                f"<details open><summary><span style='{key_style}'>{escape(key)}</span>{req_tag}</summary>"
                f"{tree_html_from_schema(schema_root, child_schema, value if isinstance(value, (dict, list)) else {})}"
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
                f"<span style='{key_style}'>{escape(key)}</span>{req_tag}: "
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
    default_mapping = (root_dir / "Metadata" / "Mappings" / "BAM2schema.json").resolve()

    state = {
        "schema_path": str(default_schema_path),
        "json_folder": str(default_json_folder),
        "json_file": "",
        "lis_folder": str(default_lis_folder),
        "lis_file": "",
        "output_name": "selected_from_lis_translated.json",
        "message": "",
        "error": "",
        "required_warnings": [],
        "required_count": 0,
        "tree_html": "",
        "schema_errors": [],
        "validated_file": "",
        "fixed_json_path": "",
        "fixed_json_preview": "",
    }

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
      <label>Schema file path</label>
      <input type="text" name="schema_path" value="{{ schema_path }}" />
    </div>

    <div class="split">
      <div>
        <h3>JSON Selection</h3>
        <div class="row">
          <label>JSON Folder</label>
          <select name="json_folder">
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
          <select name="lis_folder">
            {% for label, value in lis_folder_options %}
            <option value="{{ value }}" {% if value == lis_folder %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="row">
          <label>LIS File</label>
          <select name="lis_file">
            {% for label, value in lis_file_options %}
            <option value="{{ value }}" {% if value == lis_file %}selected{% endif %}>{{ label }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="row">
          <label>Output JSON filename</label>
          <input type="text" name="output_name" value="{{ output_name }}" />
        </div>
        <button type="submit" name="action" value="convert_lis">Convert LIS to JSON</button>
      </div>
    </div>

    <div class="row" style="margin-top:12px;">
      <button type="submit" name="action" value="validate">Run Validation</button>
            <button type="submit" name="action" value="autofix_json">Auto-fix JSON</button>
    </div>
  </form>

  {% if message %}<p class="ok">{{ message }}</p>{% endif %}
  {% if error %}<p class="error">{{ error }}</p>{% endif %}

  {% if validated_file %}
  <div class="panel">
        <h2>Validation Summary</h2>
    <p><b>File:</b> {{ validated_file }}</p>
    <p><b>Total required keywords declared:</b> {{ required_count }}</p>
    {% if required_warnings|length == 0 %}
      <p class="ok">All required keywords are defined.</p>
    {% else %}
      <p class="error">Missing or undefined required keywords: {{ required_warnings|length }}</p>
    {% endif %}

        <h2>Tree View</h2>
        <div>
            <span style="color:#0a7a2a;font-weight:600;">(required)</span> = required and defined,
            <span style="color:#a00;font-weight:700;">(required, missing)</span> = required but missing/empty.
        </div>
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

    def render_home():
        json_folder_options, json_file_options, lis_folder_options, lis_file_options = build_folder_file_options()
        return render_template_string(
            template,
            schema_path=state["schema_path"],
            json_folder=state["json_folder"],
            json_file=state["json_file"],
            lis_folder=state["lis_folder"],
            lis_file=state["lis_file"],
            output_name=state["output_name"],
            message=state["message"],
            error=state["error"],
            required_warnings=state["required_warnings"],
            required_count=state["required_count"],
            tree_html=Markup(state["tree_html"]),
            schema_errors=state["schema_errors"],
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
        state["schema_path"] = request.form.get("schema_path", state["schema_path"]).strip()
        state["json_folder"] = request.form.get("json_folder", state["json_folder"]).strip()
        state["json_file"] = request.form.get("json_file", state["json_file"]).strip()
        state["lis_folder"] = request.form.get("lis_folder", state["lis_folder"]).strip()
        state["lis_file"] = request.form.get("lis_file", state["lis_file"]).strip()
        state["output_name"] = request.form.get("output_name", state["output_name"]).strip()

        selected_action = request.form.get("action", "")
        state["message"] = ""
        state["error"] = ""

        if selected_action != "autofix_json":
            state["fixed_json_path"] = ""
            state["fixed_json_preview"] = ""

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

                schema_doc = load_json(schema_path)
                experiment_doc = load_json(json_file)

                fixed_doc, changes = autofix_experiment_json(schema_doc, experiment_doc)

                # Second pass: repair common schema errors directly from validator feedback.
                schema_target, data_target = normalize_experiment_data(schema_doc, fixed_doc)
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

                schema_doc = load_json(schema_path)
                experiment_doc = load_json(json_file)

                req_paths, warnings, schema_target, data_target = validate_required_keywords(schema_doc, experiment_doc)
                state["required_warnings"] = warnings
                state["required_count"] = len(req_paths)
                state["tree_html"] = tree_html_from_schema(schema_target, schema_target, data_target)
                state["validated_file"] = str(json_file)

                try:
                    from jsonschema import Draft201909Validator
                except ImportError as exc:
                    raise ImportError(
                        "jsonschema is not installed. Install it with: pip install jsonschema"
                    ) from exc

                validator = Draft201909Validator(schema_target)
                errors = sorted(validator.iter_errors(data_target), key=lambda e: list(e.path))

                schema_errors = []
                for err in errors[:200]:
                    schema_errors.append(
                        {
                            "data_path": ".".join([str(p) for p in err.path]) if list(err.path) else "<root>",
                            "message": str(err.message),
                            "schema_path": "/".join([str(p) for p in err.schema_path]),
                        }
                    )
                state["schema_errors"] = schema_errors
                state["message"] = "Validation completed."
            except Exception as exc:
                state["error"] = f"Validation failed: {exc}"

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
