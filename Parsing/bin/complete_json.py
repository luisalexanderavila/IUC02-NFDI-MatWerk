import argparse
import json
import sys
from pathlib import Path

import validation_core


DEFAULT_SCHEMA_FILE = (Path(__file__).resolve().parents[1] / ".." / "Data Schema" / "2026-03_Data-Schema_Creep_v2.1.json").resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fill missing required metadata fields and revalidate.")
    parser.add_argument("--file", required=True, help="Input JSON file to complete.")
    parser.add_argument("--schema", default=str(DEFAULT_SCHEMA_FILE), help="Path to JSON schema.")
    parser.add_argument("--fill", default=None, help="Optional JSON or YAML file with path->value completions.")
    parser.add_argument("--output", default=None, help="Output path for completed JSON.")
    parser.add_argument("--non-interactive", action="store_true", help="Fail if unresolved required fields remain.")
    return parser.parse_args()


def load_fill_map(path: Path) -> dict:
    suffix = path.suffix.lower()
    if suffix == ".json":
        with path.open("r", encoding="utf-8") as handle:
            obj = json.load(handle)
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError as exc:
            raise RuntimeError("PyYAML is required for YAML fill files. Install with: pip install pyyaml") from exc
        with path.open("r", encoding="utf-8") as handle:
            obj = yaml.safe_load(handle)
    else:
        raise ValueError("--fill must be .json, .yaml, or .yml")

    if not isinstance(obj, dict):
        raise ValueError("Fill file must contain an object/dictionary at root")
    return obj


def path_to_parts(path_str: str):
    return tuple(part for part in path_str.split(".") if part)


def get_schema_for_path(schema_root: dict, path_parts: tuple[str, ...]):
    node = validation_core.resolve_ref(schema_root, schema_root)
    for part in path_parts:
        node = validation_core.resolve_ref(schema_root, node)
        props = node.get("properties", {}) if isinstance(node, dict) else {}
        if isinstance(props, dict) and part in props:
            node = props[part]
            continue
        items = node.get("items") if isinstance(node, dict) else None
        if part == "*" and isinstance(items, dict):
            node = items
            continue
        return {}
    return validation_core.resolve_ref(schema_root, node)


def set_by_path(root_obj: dict, path_parts: tuple[str, ...], value):
    current = root_obj
    for idx, part in enumerate(path_parts):
        is_last = idx == len(path_parts) - 1
        if is_last:
            current[part] = value
            return
        if part not in current or not isinstance(current[part], dict):
            current[part] = {}
        current = current[part]


def normalize_for_data_target(path_str: str) -> str:
    if path_str.startswith("MeasurementData."):
        return path_str
    return f"MeasurementData.{path_str}" if not path_str.startswith("mappedMeasurementData") else path_str


def prompt_for_value(path: str, schema_node: dict):
    enum_values = schema_node.get("enum", []) if isinstance(schema_node, dict) else []
    if isinstance(enum_values, list) and enum_values:
        print(f"\nSelect value for {path}:")
        for idx, item in enumerate(enum_values, start=1):
            print(f"  {idx}. {item}")
        while True:
            raw = input("Choice number: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(enum_values):
                return enum_values[int(raw) - 1]
            print("Invalid choice, try again.")

    node_type = schema_node.get("type") if isinstance(schema_node, dict) else None
    if node_type == "object":
        props = schema_node.get("properties", {}) if isinstance(schema_node, dict) else {}
        if "value" in props and "unit" in props:
            raw_value = input(f"Enter value for {path}.value: ").strip()
            raw_unit = input(f"Enter value for {path}.unit: ").strip()
            return {"value": raw_value, "unit": raw_unit}

    return input(f"Enter value for {path}: ").strip()


def main() -> int:
    args = parse_args()

    schema_path = Path(args.schema)
    json_path = Path(args.file)

    if not schema_path.exists():
        raise FileNotFoundError(f"Schema not found: {schema_path}")
    if not json_path.exists():
        raise FileNotFoundError(f"Input JSON not found: {json_path}")

    schema_doc = validation_core.load_json(schema_path)
    doc = validation_core.load_json(json_path)

    fill_map = {}
    if args.fill:
        fill_map = load_fill_map(Path(args.fill))

    req_paths, warnings, schema_target, data_target = validation_core.validate_required_keywords(schema_doc, doc)

    # apply supplied fill values first
    for warning in warnings:
        warning_path = warning["path"]
        if warning_path in fill_map:
            path_parts = path_to_parts(warning_path)
            set_by_path(data_target, path_parts, fill_map[warning_path])

    # recompute after fill map application
    _, warnings, schema_target, data_target = validation_core.validate_required_keywords(schema_doc, doc)

    if warnings and not args.non_interactive:
        print(f"Missing required fields: {len(warnings)}")
        for warning in warnings:
            warning_path = warning["path"]
            schema_node = get_schema_for_path(schema_target, path_to_parts(warning_path))
            value = prompt_for_value(warning_path, schema_node)
            set_by_path(data_target, path_to_parts(warning_path), value)

    _, unresolved, schema_target, data_target = validation_core.validate_required_keywords(schema_doc, doc)
    schema_errors = validation_core.run_jsonschema_validation(schema_target, data_target)

    if args.non_interactive and unresolved:
        print(json.dumps({"unresolved_required": unresolved}, indent=2, ensure_ascii=False))
        return 1

    output_path = Path(args.output) if args.output else json_path.with_name(f"{json_path.stem}_completed{json_path.suffix}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2, ensure_ascii=False)

    print(f"Completed file written: {output_path}")
    print(f"Remaining missing required: {len(unresolved)}")
    print(f"Schema errors: {len(schema_errors)}")

    return 0 if not unresolved and not schema_errors else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Completion failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
