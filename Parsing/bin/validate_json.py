import argparse
import json
import os
import sys
from pathlib import Path

import validation_core


DEFAULT_SCHEMA_FILE = (Path(__file__).resolve().parents[1] / ".." / "Data Schema" / "2025-12_Data-Schema_Creep_v2.0.json").resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate metadata JSON file(s) against required fields and JSON schema.")
    parser.add_argument("--file", dest="file", help="Single JSON file to validate.")
    parser.add_argument("--folder", dest="folder", help="Folder to recursively validate all JSON files.")
    parser.add_argument("--schema", dest="schema", default=str(DEFAULT_SCHEMA_FILE), help="Path to schema JSON file.")
    parser.add_argument("--format", dest="fmt", choices=["text", "json"], default="text", help="Output format.")
    parser.add_argument("--output", dest="output", default=None, help="Optional report output path (JSON).")
    return parser.parse_args()


def iter_input_files(file_arg: str | None, folder_arg: str | None):
    if file_arg and folder_arg:
        raise ValueError("Use either --file or --folder, not both.")
    if not file_arg and not folder_arg:
        raise ValueError("Provide --file or --folder.")

    if file_arg:
        path = Path(file_arg)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(f"Input file not found: {path}")
        return [path]

    folder = Path(folder_arg)
    if not folder.exists() or not folder.is_dir():
        raise FileNotFoundError(f"Input folder not found: {folder}")
    return sorted([p for p in folder.rglob("*.json") if p.is_file()])


def validate_one(file_path: Path, schema_doc: dict):
    experiment_doc = validation_core.load_json(file_path)
    req_paths, warnings, schema_target, data_target = validation_core.validate_required_keywords(schema_doc, experiment_doc)
    schema_errors = validation_core.run_jsonschema_validation(schema_target, data_target)
    return {
        "file": str(file_path),
        "required_total": len(req_paths),
        "missing_required": len(warnings),
        "required_warnings": warnings,
        "schema_error_count": len(schema_errors),
        "schema_errors": schema_errors,
        "is_valid": len(warnings) == 0 and len(schema_errors) == 0,
    }


def main() -> int:
    args = parse_args()

    schema_path = Path(args.schema)
    if not schema_path.exists() or not schema_path.is_file():
        raise FileNotFoundError(f"Schema not found: {schema_path}")

    schema_doc = validation_core.load_json(schema_path)
    files = iter_input_files(args.file, args.folder)

    reports = [validate_one(path, schema_doc) for path in files]
    invalid_count = sum(1 for report in reports if not report["is_valid"])

    summary = {
        "schema": str(schema_path),
        "file_count": len(reports),
        "invalid_count": invalid_count,
        "reports": reports,
    }

    if args.fmt == "json":
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print(f"Schema: {schema_path}")
        print(f"Files checked: {len(reports)}")
        print(f"Invalid files: {invalid_count}")
        for report in reports:
            status = "OK" if report["is_valid"] else "FAIL"
            print(f"- [{status}] {report['file']}")
            if not report["is_valid"]:
                print(f"  missing_required={report['missing_required']}, schema_errors={report['schema_error_count']}")

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(summary, handle, indent=2, ensure_ascii=False)

    return 0 if invalid_count == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
