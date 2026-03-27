import json
import os
import sys
import tempfile
import unittest
import logging
from pathlib import Path

PARSING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARSING_DIR / "dependencies" / "Mappingsreader"))
sys.path.insert(0, str(PARSING_DIR / "dependencies" / "LISParser"))

from mappingsreader.mapreader import read_mapping, translate_bam, translate_generic
from LISParser.LisParse import Parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

class TestReadsMapping(unittest.TestCase):

    def setUp(self):
        self.reads_mapping_file = PARSING_DIR / "Metadata" / "Mappings" / "BAM2schema.json"
        with open(self.reads_mapping_file, "r", encoding="utf-8") as handle:
            self.mapping_document = json.load(handle)
        logging.info("Loaded mapping document")

    def test_read_reads_mapping(self):
        self.assertLess(0, len(self.mapping_document))

    def test_mapping_reader(self):
        mapping = read_mapping(self.reads_mapping_file)
        self.assertLess(0, len(mapping))
        self.assertTrue(isinstance(mapping, dict))
    
class TestFillsSchema(unittest.TestCase):
    def setUp(self):
        self.reads_mapping_file = PARSING_DIR / "Metadata" / "Mappings" / "BAM2schema.json"
        with open(self.reads_mapping_file, "r", encoding="utf-8") as handle:
            self.mapping_document = json.load(handle)
        self.placeholder_schema = read_mapping(self.reads_mapping_file)
        self.placeholder_schema_file = Path(tempfile.gettempdir()) / "placeholder_schema.json"
        with open(self.placeholder_schema_file, 'w', encoding="utf-8") as file:
            json.dump(self.placeholder_schema, file, indent=4)
        logging.info('Loaded mapping document')

        self.lisfile = PARSING_DIR / 'Data' / 'BAMDataset' / 'Vh5205_C-78.LIS'
        lis_parser = Parser(str(self.lisfile))
        self.lis_dict = lis_parser.parse_lis()
        self.translated_dict = translate_bam(self.lis_dict['metadata'], self.mapping_document)

    def test_got_mapping_doc(self):
        self.assertLess(0, len(self.placeholder_schema))
        self.assertTrue(isinstance(self.placeholder_schema, dict))

    def test_is_nested(self):
        self.assertTrue(isinstance(self.placeholder_schema, dict))
        self.assertTrue('MeasurementData' in self.placeholder_schema)
        self.assertTrue(self.placeholder_schema["MeasurementData"]["additionalMetadata"][ "testInfo" ][ "testJobDetails" ]["dateOfTestStart"] is not None)
#    
    def test_got_lis_dict(self):
        self.assertLess(0, len(self.lis_dict))
        self.assertTrue(isinstance(self.lis_dict, dict))
#
    def test_translate_bam(self):
        translated_dict_file = Path(tempfile.gettempdir()) / f"{self.lisfile.stem}_translated.json"
        with open(translated_dict_file, 'w', encoding="utf-8") as file:
            json.dump(self.translated_dict, file, indent=4)
        self.assertTrue(isinstance(self.translated_dict, dict))


    def test_parsed_correctly(self):
        self.assertTrue(isinstance(
        self.translated_dict["mappedMeasurementData"]["MeasurementData"]['additionalMetadata']["testInfo"]["testParameters"]["specifiedTemperature"]["value"],
        float
        ))
        self.assertTrue(
        self.translated_dict["mappedMeasurementData"]["MeasurementData"]['additionalMetadata']["testInfo"]["testParameters"]["specifiedTemperature"]["unit"] \
        in ['C', 'F']
        )

if __name__ == '__main__':
    unittest.main()
