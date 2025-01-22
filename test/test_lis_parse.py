from LISParser  import Parser
import unittest

class TestReadLisFile(unittest.TestCase):

    def setUp(self):
        self.lis_file = 'Data/BAMDataset/Vh5205_C-78.LIS'
        self.parser = Parser(self.lis_file)

    def test_read_lis_file(self):
        thedict = self.parser.parse_lis()
        self.assertLess(0, len(thedict))

if __name__ == '__main__':
    unittest.main()