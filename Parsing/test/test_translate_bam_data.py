import json
import copy
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class TestTranslateBamData(unittest.TestCase):
    def setUp(self):
        self.parsing_dir = Path(__file__).resolve().parents[1]
        self.script = self.parsing_dir / "bin" / "translate_bam_data.py"
        self.lis_file = self.parsing_dir / "Data" / "BAMDataset_v032026" / "Vh5205_C-78-MD-TR.lis"
        self.mapping_file = self.parsing_dir / "Metadata" / "Mappings" / "BAM2schema.json"
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

    def test_derives_measurement_method_from_complementary_measured_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_file = Path(tmp) / "converted.json"
            mapping_override = Path(tmp) / "mapping_without_measurement_method.json"

            mapping_doc = json.loads(self.mapping_file.read_text(encoding="utf-8-sig"))
            mapped = copy.deepcopy(mapping_doc.get("mappedMeasurementData", {}))
            mapped.pop(
                "metadata.material history and condition.chemical composition.measurement method",
                None,
            )
            mapping_doc["mappedMeasurementData"] = mapped
            mapping_override.write_text(json.dumps(mapping_doc, indent=2), encoding="utf-8")

            cmd = [
                sys.executable,
                str(self.script),
                str(self.lis_file),
                "--mapping",
                str(mapping_override),
                "--output",
                str(output_file),
            ]
            result = subprocess.run(cmd, cwd=self.parsing_dir, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            converted = json.loads(output_file.read_text(encoding="utf-8"))
            measurement_method = (
                converted
                .get("MeasurementData", {})
                .get("AdditionalMetadata", {})
                .get("MaterialHistoryAndCondition", {})
                .get("chemicalComposition", [{}])[0]
                .get("measurementMethod")
            )

            self.assertIsInstance(measurement_method, str)
            self.assertIn("Atomic Absorption", measurement_method)

            measured_elements = (
                converted
                .get("MeasurementData", {})
                .get("AdditionalMetadata", {})
                .get("MaterialHistoryAndCondition", {})
                .get("chemicalComposition", [{}])[0]
                .get("chemicalCompositionMeasured", [])
            )
            self.assertIsInstance(measured_elements, list)
            self.assertGreater(len(measured_elements), 0)
            self.assertIn("measurementMethod", measured_elements[0])


if __name__ == "__main__":
    unittest.main()
