import json
import os
import sys
import logging
import pdb

from creep_shacl_maker.shacl_maker import header, write_shacl_metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(__file__))




if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_json', type=str, help='input json file with  creep test metadata')
    parser.add_argument('-o', '--output', type=str, dest='output_ttl',  help='output shacl file', default=None)
    args = parser.parse_args()
    if args.output_ttl is None:
        args.output_ttl = os.path.splitext(args.input_json)[0] + '.ttl'
    
    logger.info(f'input json file: {args.input_json}')
    logger.info(f'output json file: {args.output_ttl}')

    with open(args.input_json, 'r') as f:
        json_metadata = json.load(f)
    logger.info(f'keys : {json_metadata.keys()}')
    json_metadata = json_metadata['mappedMeasurementData']["MeasurementData"]["additionalMetadata"]

    shacl_metadata = write_shacl_metadata(json_metadata)

    with open(args.output_ttl, 'w') as f:
        f.writelines(header)
        f.writelines(shacl_metadata)

		


    #

