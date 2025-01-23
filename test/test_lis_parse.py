from LISParser  import Parser
import unittest
import json
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__file__)

class TestReadLisFile(unittest.TestCase):

    def setUp(self):
        self.lis_file = 'Data/BAMDataset/Vh5205_C-78.LIS'
        self.parser = Parser(self.lis_file)
        self.jsonfile = self.lis_file.replace('LIS', 'json')
        self.thedict = self.parser.parse_lis()
        logger.info(f'Writing json file: {self.jsonfile}')
        with open(self.jsonfile, 'w') as f:
            json.dump(self.thedict, f, indent=4)

    def test_read_lis_file(self):
        self.assertLess(0, len(self.thedict))

    def test_data_titles(self):
        logging.info(f'test data titles')
        logging.info(f'data_titles: {self.thedict["data"].keys()}')


if __name__ == '__main__':
    unittest.main()