import sys
import unittest
from pathlib import Path

PARSING_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PARSING_DIR / "dependencies" / "LISParser"))

from LISParser.LisParse import Parser

class TestReadLisFile(unittest.TestCase):

    def setUp(self):
        self.lis_file = PARSING_DIR / "Data" / "BAMDataset" / "Vh5205_C-78.LIS"
        self.parser = Parser(str(self.lis_file))
        self.thedict = self.parser.parse_lis()

    def test_read_lis_file(self):
        self.assertLess(0, len(self.thedict))

    def test_data_titles(self):
        self.assertIn("data", self.thedict)
        self.assertGreater(len(self.thedict["data"].keys()), 0)

if __name__ == '__main__':
    unittest.main()