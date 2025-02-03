import json
import os
import pdb
import unittest
import logging
from mappingsreader.mapreader import read_mapping, translate_bam, translate_generic
from LISParser.LisParse import Parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

class TestReadsMapping(unittest.TestCase):

    def setUp(self):
        self.reads_mapping_file = 'Metadata/Mappings/BAM2schema.json'
        self.mapping_document = json.load(open(self.reads_mapping_file))
        logging.info(f'Loaded mapping document')

    def test_read_reads_mapping(self):
        self.assertLess(0, len(self.mapping_document))

    def test_mapping_reader(self):
        mapping = read_mapping(self.reads_mapping_file)
        self.assertLess(0, len(mapping))
        self.assertTrue(isinstance(mapping, dict))
    
class TestFillsSchema(unittest.TestCase):
    def setUp(self):
        self.reads_mapping_file = 'Metadata/Mappings/BAM2schema.json'
        self.mapping_document = json.load(open(self.reads_mapping_file))
        self.placeholder_schema = read_mapping(self.reads_mapping_file)
        self.placeholder_schema_file = os.path.join(os.path.dirname(self.reads_mapping_file), 'placeholder_schema.json')
        with open(self.placeholder_schema_file, 'w') as file:
            json.dump(self.placeholder_schema, file, indent=4)
        logging.info(f'Loaded mapping document')

        self.lisfile = 'Data/BAMDataset/Vh5205_C-78.LIS'
        lis_parser = Parser(self.lisfile)
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
        translated_dict_file = self.lisfile.replace('.LIS','_translated.json')
        with open(translated_dict_file, 'w') as file:
            json.dump(self.translated_dict, file, indent=4)
        self.assertTrue(isinstance(translated_dict, dict))


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
