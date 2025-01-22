import os
import sys
import pdb
import json
import re
import numpy as np
import pdb
import logging
from tqdm.auto import tqdm
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


def get_key_value(key_value_line: str):
    splitted = key_value_line.split('\t')
    key = splitted[0].strip()
    value = ''.join(splitted[ 1: ]).strip()
    return key, value

class Parser():

    def __init__(self, filename, ecncoding='latin1'):
        self.file_lines = self.read_lis(filename)


    def read_lis(self,filename):
        with open(filename, 'r', encoding='latin1') as f:
            raw_lines = f.readlines()
        file_lines = []

        for line in raw_lines:
            file_lines.append(line.strip())
        return file_lines

    def parse_lis(self):
        raw_file_content = self.file_lines

        json_content = {'title': raw_file_content[0], 'metadata':{}, 'data':{}}


        for ln, line in enumerate(raw_file_content[2:]):
            if len(line) < 1:
                continue
            if  ( len(line.strip()) == 0 ):
                continue
            if ( '[data]' in line ):
                break
            key, value = get_key_value(line)
            logger.info(f'key: {key}, value: {value}')

            json_content['metadata'][key] = value

        logger.info(f'[data] data starts at line {ln+2}')

        data_titles = raw_file_content[ln+1].split('\t')
        data_symbols = raw_file_content[ln+2].split('\t')
        data_units = raw_file_content[ln+3].split('\t')
        if len(data_titles) != len(data_units):
            logger.error(f'Error: data_titles and data_units have different lengths')
        for title, unit in zip(data_titles, data_units):
            json_content['data'][title] = {'unit' : unit, 'values' : []}
        
        progress = tqdm(enumerate(raw_file_content[ln+4:]), total=len(raw_file_content[ln+4:]))
        for ln3, line in progress: #enumerate(raw_file_content[ln+4:]):
            if len(line) == 0:
                continue
            values = np.fromstring(line.replace(',','.'), sep='\t', )
            for title, value in zip(data_titles, values):
                json_content['data'][title]['values'].append(value)
#                json_content['data'][data_titles[0]]['values'].append(x)
#                json_content['data'][data_titles[1]]['values'].append(y)
        return json_content




if __name__ == '__main__':
    filename = sys.argv[1] 
    srcdir = os.path.dirname(filename)
    json_file = filename.replace('LIS', 'json')
    data = Data(sys.argv[1])
    jsoned_data = data.parse_lis()
    with open(json_file, 'w') as f:
        json.dump(jsoned_data, f,indent=True)
        

        
