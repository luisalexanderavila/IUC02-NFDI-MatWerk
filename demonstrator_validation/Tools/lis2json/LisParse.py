import os
import sys
import pdb
import json
import re
import numpy as np


def get_key_value(key_value_line: str):
    splitted = key_value_line.split('\t')
    key = splitted[0].strip()
    value = ''.join(splitted[ 1: ]).strip()
    return key, value


class Data():

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
            if line[0] == '-' and len(json_content['metadata']) > 0:
                break
            key, value = get_key_value(line)

            json_content['metadata'][key] = value

        for ln2, line in enumerate(raw_file_content[ln+2:]):
            if '[Daten]' in line:
                break
        data_titles = raw_file_content[ln+ln2+2+1].split()
        data_units = raw_file_content[ln+ln2+2+2].split()
        json_content['data'][data_titles[0]] = {'unit' : data_units[0], 'values' : []}
        json_content['data'][data_titles[1]] = {'unit' : data_units[1], 'values' : []}
        for ln3, line in enumerate(raw_file_content[ln+ln2+2+2+3:]):
            if len(line) == 0:
                continue
            x, y = np.fromstring(line.replace(',','.'), sep='\t', )
            json_content['data'][data_titles[0]]['values'].append(x)
            json_content['data'][data_titles[1]]['values'].append(y)
        return json_content




if __name__ == '__main__':
    filename = sys.argv[1] 
    srcdir = os.path.dirname(filename)
    json_file = filename.replace('LIS', 'json')
    data = Data(sys.argv[1])
    jsoned_data = data.parse_lis()
    with open(json_file, 'w') as f:
        json.dump(jsoned_data, f,indent=True)
        

        
