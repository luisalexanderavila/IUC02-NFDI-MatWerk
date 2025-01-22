from LISParser  import Parser
import unittest

import logging
logging.basicConfig(level=logging.DEBUG)
logger=logging.getLogger(__name__)
logger.info("hello worlds")

class TestReadLisFile(unittest.TestCase):

    def setUp(self):
        logger.info("Setting up test")
        self.lis_file = 'Data/BAMDataset/Vh5205_C-78.LIS'
        self.parser = Parser(self.lis_file)

    def test_read_lis_file(self):
        logger.info("Testing read_lis_file")
        thedict = self.parser.parse_lis()
        self.assertLess(0, len(thedict))

if __name__ == '__main__':
    unittest.main()
