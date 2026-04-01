import json
import subprocess
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    parsing = Path(__file__).resolve().parents[1]
    script_translate = parsing / "bin" / "translate_bam_data_v2.py"
    script_validate = parsing / "bin" / "validate_json.py"
    schema = parsing.parent / "Data Schema" / "2025-12_Data-Schema_Creep_v2.0.json"

    lis_dir = parsing / "Data" / "BAMDataset_v032026"
    out_dir = lis_dir / "_batch_translated"
    out_dir.mkdir(parents=True, exist_ok=True)

    lis_files = sorted(lis_dir.glob("*-MD-TR.lis"))

    results = []
    error_counter = Counter()
    missing_counter = Counter()

    for lis in lis_files:
        out_json = out_dir / f"{lis.stem}_schema_v2.json"
        translate_cmd = [
            sys.executable,
            str(script_translate),
            str(lis),
            "--output",
            str(out_json),
        ]
        t = subprocess.run(translate_cmd, cwd=str(parsing), capture_output=True, text=True)

        item = {
            "file": str(lis),
            "translated": t.returncode == 0,
            "translate_returncode": t.returncode,
        }
        if t.returncode != 0:
            item["translate_stderr_tail"] = (t.stderr or "")[-2000:]
            results.append(item)
            continue

        validate_cmd = [
            sys.executable,
            str(script_validate),
            "--file",
            str(out_json),
            "--schema",
            str(schema),
            "--format",
            "json",
        ]
        v = subprocess.run(validate_cmd, cwd=str(parsing), capture_output=True, text=True)

        try:
            payload = json.loads(v.stdout) if v.stdout.strip() else {}
        except Exception:
            payload = {}

        rep = (payload.get("reports") or [{}])[0]
        missing = rep.get("required_warnings", []) or []
        schema_errors = rep.get("schema_errors", []) or []

        for warning in missing:
            path = warning.get("path")
            if path:
                missing_counter[path] += 1
        for schema_error in schema_errors:
            message = schema_error.get("message")
            if message:
                error_counter[message] += 1

        item.update(
            {
                "validate_returncode": v.returncode,
                "is_valid": rep.get("is_valid", False),
                "missing_required": rep.get("missing_required", 0),
                "schema_error_count": rep.get("schema_error_count", 0),
            }
        )
        results.append(item)

    summary = {
        "files_total": len(lis_files),
        "translated_ok": sum(1 for row in results if row.get("translated")),
        "valid_total": sum(1 for row in results if row.get("is_valid")),
        "invalid_total": sum(1 for row in results if row.get("translated") and not row.get("is_valid")),
        "top_missing_required": missing_counter.most_common(20),
        "top_schema_errors": error_counter.most_common(20),
        "results": results,
    }

    report_json = parsing / "Doc" / "v032026_batch_validation_report.json"
    report_md = parsing / "Doc" / "v032026_batch_validation_report.md"
    report_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    lines = [
        "# v032026 Batch Validation Report",
        "",
        f"- Files checked: {summary['files_total']}",
        f"- Translated OK: {summary['translated_ok']}",
        f"- Fully valid: {summary['valid_total']}",
        f"- Invalid after translation: {summary['invalid_total']}",
        "",
        "## Invalid Files",
    ]
    for row in summary["results"]:
        if row.get("translated") and not row.get("is_valid"):
            lines.append(
                f"- {Path(row['file']).name}: missing_required={row.get('missing_required', 0)}, schema_errors={row.get('schema_error_count', 0)}"
            )

    lines.append("")
    lines.append("## Top Missing Required Paths")
    for path, count in summary["top_missing_required"]:
        lines.append(f"- {path}: {count}")

    lines.append("")
    lines.append("## Top Schema Error Messages")
    for message, count in summary["top_schema_errors"]:
        lines.append(f"- {message}: {count}")

    report_md.write_text("\n".join(lines), encoding="utf-8")

    print(
        json.dumps(
            {
                "files_total": summary["files_total"],
                "translated_ok": summary["translated_ok"],
                "valid_total": summary["valid_total"],
                "invalid_total": summary["invalid_total"],
                "report_json": str(report_json),
                "report_md": str(report_md),
            },
            indent=2,
        )
    )
    return 0 if summary["invalid_total"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
