import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestNewFeatures(unittest.TestCase):
    def setUp(self):
        self.parsing_dir = Path(__file__).resolve().parents[1]
        self.translate_script = self.parsing_dir / "bin" / "translate_bam_data.py"
        self.validate_script = self.parsing_dir / "bin" / "validate_json.py"
        self.batch_script = self.parsing_dir / "bin" / "run_batch_validation.py"
        self.schema_file = self.parsing_dir.parent / "Data Schema" / "2026-06_Data-Schema_Creep_v2.1.8.json"
        # This file uses additionalMetadata --> ... for several rows.
        self.alias_lis_file = self.parsing_dir / "Data" / "BAMDataset_v20260608" / "Vh5205_C-82-MD-TR.lis"

    def test_additional_metadata_alias_parses_and_validates(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "c82_converted.json"

            convert_cmd = [
                sys.executable,
                str(self.translate_script),
                str(self.alias_lis_file),
                "--output",
                str(output_file),
            ]
            convert = subprocess.run(convert_cmd, cwd=self.parsing_dir, capture_output=True, text=True)
            self.assertEqual(convert.returncode, 0, msg=convert.stderr)
            self.assertTrue(output_file.exists())

            validate_cmd = [
                sys.executable,
                str(self.validate_script),
                "--file",
                str(output_file),
                "--schema",
                str(self.schema_file),
                "--format",
                "json",
            ]
            validate = subprocess.run(validate_cmd, cwd=self.parsing_dir, capture_output=True, text=True)
            self.assertEqual(validate.returncode, 0, msg=validate.stderr)

            payload = json.loads(validate.stdout)
            report = payload["reports"][0]
            self.assertTrue(report["is_valid"])
            self.assertEqual(report["missing_required"], 0)
            self.assertEqual(report["schema_error_count"], 0)

    def test_batch_validation_runner_reports_success(self):
        run = subprocess.run(
            [sys.executable, str(self.batch_script)],
            cwd=self.parsing_dir,
            capture_output=True,
            text=True,
        )
        self.assertIn(run.returncode, (0, 1), msg=run.stderr)

        report_json = self.parsing_dir / "Doc" / "v032026_batch_validation_report.json"
        self.assertTrue(report_json.exists())

        summary = json.loads(report_json.read_text(encoding="utf-8"))
        self.assertGreater(summary["files_total"], 0)
        self.assertEqual(summary["translated_ok"], summary["files_total"])
        self.assertEqual(summary["invalid_total"], 0)


if __name__ == "__main__":
    unittest.main()
