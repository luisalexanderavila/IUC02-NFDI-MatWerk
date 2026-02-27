import os
import sys
import json

from Tools.SchemaUpdater import SchemaUpdater
from Tools.lis2json import LisParse
from Tools.Metainfo import metainfo


schema_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Data Schema IUC02/schema_creep_test.json')

def load_schema(
        filename = schema_file 
        ):

    with open(schema_file, 'r') as f:
        schema = json.load(f)

    return schema

