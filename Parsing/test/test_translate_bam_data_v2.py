import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestTranslateBamDataV2(unittest.TestCase):
    def setUp(self):
        self.parsing_dir = Path(__file__).resolve().parents[1]
        self.script = self.parsing_dir / "bin" / "translate_bam_data_v2.py"
        self.lis_file = self.parsing_dir / "Data" / "BAMDataset_v032026" / "Vh5205_C-78-MD-TR.lis"
        self.mapping_file = self.parsing_dir / "Metadata" / "Mappings" / "BAM2schema_v2.json"
        self.schema_file = self.parsing_dir.parent / "Data Schema" / "2025-12_Data-Schema_Creep_v2.0.json"

    def test_v2_conversion_creates_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "converted.json"
            cmd = [
                sys.executable,
                str(self.script),
                str(self.lis_file),
                "--mapping",
                str(self.mapping_file),
                "--output",
                str(output_file),
            ]
            result = subprocess.run(cmd, cwd=self.parsing_dir, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(output_file.exists())

            converted = json.loads(output_file.read_text(encoding="utf-8"))
            self.assertEqual(converted.get("_lis_version"), "v2")
            self.assertEqual(converted.get("_schema_version"), "2025-12")
            self.assertIn("MeasurementData", converted)

    def test_v2_schema_validation_generates_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "converted.json"
            report_file = Path(tmp) / "validation_report.json"
            cmd = [
                sys.executable,
                str(self.script),
                str(self.lis_file),
                "--mapping",
                str(self.mapping_file),
                "--output",
                str(output_file),
                "--validate-schema",
                str(self.schema_file),
                "--validation-report",
                str(report_file),
            ]
            result = subprocess.run(cmd, cwd=self.parsing_dir, capture_output=True, text=True)
            self.assertIn(result.returncode, (0, 2), msg=result.stderr)
            self.assertTrue(report_file.exists())

            report = json.loads(report_file.read_text(encoding="utf-8"))
            self.assertIn("error_count", report)
            self.assertIn("errors", report)
            self.assertIsInstance(report["error_count"], int)
            self.assertIsInstance(report["errors"], list)

            if report["error_count"] > 0:
                first_error = report["errors"][0]
                self.assertIn("path", first_error)
                self.assertIn("message", first_error)


if __name__ == "__main__":
    unittest.main()
