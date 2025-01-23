import json
import os
import pdb

def read_mapping(file_path: os.PathLike) -> dict:
    with open(file_path, 'r') as file:
        data = json.load(file)

    def set_nested_value(d, keys, value):
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    result = {}
    for value, keysstr in data["mappedMeasurementData"].items():
        keys = keysstr.split('.')
        set_nested_value(result, keys, value)

    return result

def get_nested_value(d, keys):
    for key in keys:
        d = d.get(key, {})
        if not isinstance(d, dict):
            return d
    return d

def translate_bam(lis_dict: dict, mapping: dict) -> dict:
    def translate(mapping, lis_dict):
        result = {}
        for key, value in mapping.items():
            if isinstance(value, dict):
                result[key] = translate(value, lis_dict)
            else:
                keys = value.split('.')
                thestring = lis_dict['metadata']['key'].split('_')[0]
                if 'value' in thestring:
                    assing='value'
                if 'unit' in thestring:
                    assing='unit'
                nested_value = get_nested_value(lis_dict, keys)
                result[key] = nested_value
        return result

    return translate(mapping, lis_dict)