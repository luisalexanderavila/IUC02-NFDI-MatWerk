import json
import os
import logging
from mappingsreader.mapreader import read_mapping, translate_bam
from LISParser.LisParse import Parser
import glob
import argparse
import pdb

logging.basicConfig(level=logging.INFO)
Logger = logging.getLogger(__name__)

argumentparser = argparse.ArgumentParser(
    prog = 'translate_bam_data.py',
    description='Translate BAM data to schema',
    epilog='''This script reads BAM files and translates the data to a schema'''
)

argumentparser.add_argument('filename',
    help='BAM file to translate',
    type=str)

argumentparser.add_argument(
    '--output',
    '-o',
    dest='output',
    help='Output file name. If None, will assign renamed input to json.', 
    type=str,
    default=None)

args = argumentparser.parse_args()

SchemaFile = 'Metadata/Mappings/BAM2schema.json'

Logger.info(f'reading input file {args.filename}')
Logger.info(f'Using schema in {SchemaFile}')


def main():
    mapping_document = json.load(open(SchemaFile, 'r'))
#placeholder_schema = read_mapping(SchemaFile)
    lis_parser = Parser(args.filename)
    lis_dict = lis_parser.parse_lis()
    translate_dict = translate_bam(lis_dict['metadata'], mapping_document)
    if args.output is None:
        output_file = os.path.splitext(args.filename)[0] + '_translated.json'
    else:
        output_file = args.output
    with open(output_file, 'w') as output:
        json.dump(translate_dict, output, indent=4)

if __name__ == '__main__':
    main()




