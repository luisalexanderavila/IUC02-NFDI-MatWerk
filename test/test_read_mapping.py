import json
import unittest
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

class TestReadsMapping(unittest.TestCase):

    def setUp(self):
        self.reads_mapping_file = 'Metadata/mappings/lis2creepschema.json'
        self.mapping_document = json.load(open(self.reads_mapping_file))
        logging.info(f'Loaded mapping document: {self.mapping_document}')


    def test_read_reads_mapping(self):
        self.assertLess(0, len(self.mapping_document))


if __name__ == '__main__':
    unittest.main()