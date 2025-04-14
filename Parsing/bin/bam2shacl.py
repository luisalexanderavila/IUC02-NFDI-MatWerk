import json
import os
import logging
from mappingsreader.mapreader import read_mapping, translate_bam
from LISParser.LisParse import Parser
import glob
import argparse
import pdb
from creep_shacl_maker.shacl_maker import header, write_shacl_metadata

logging.basicConfig(level=logging.INFO)
Logger = logging.getLogger(__name__)

mapping_document = json.load(open('Metadata/Mappings/BAM2schema.json', 'r'))

if __name__ == '__main__':

    argparser = argparse.ArgumentParser(
            prog='bam2ttl.py',
            description='Translate BAM data to ttl graph',
            epilog='''This script reads BAM files and translates the data to a ttl graph'''

            )
    argparser.add_argument(
            '--input', 
            '-i',
            help='BAM file to translate',
            dest='filename',
            type=str)

    argparser.add_argument(
            '--output',
            '-o',
            dest='output',
            help='Output file name. If None, will assign renamed input to json.',
            type=str,
            default=None)

    args = argparser.parse_args()

    if not os.path.exists(args.filename):
        Logger.error(f'Input file {args.filename} does not exist')
        exit(1)

    if args.output is None:
        args.output = os.path.splitext(args.filename)[0] + '_translated.ttl'

    if not os.path.exists(os.path.dirname(args.output)):
        Logger.error(f'Output directory {os.path.dirname(args.output)} does not exist, I will create it')
        os.makedirs(os.path.dirname(args.output))

    lis_parser = Parser(args.filename)
    lis_dict = lis_parser.parse_lis()
    translate_dict = translate_bam(lis_dict['metadata'], mapping_document)
    json_metadata = translate_dict['mappedMeasurementData']["MeasurementData"]["additionalMetadata"]
    shacl_metadata = write_shacl_metadata(json_metadata)

    with open(args.output, 'w') as f:
        f.writelines(header)
        f.writelines(shacl_metadata)










