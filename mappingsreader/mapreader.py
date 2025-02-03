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

def set_nested_value(d, keys, value):
    for key in keys[:-1]:
        d = d.setdefault(key, {})
    d[keys[-1]] = value

import re
def translate_bam(lis_dict: dict, mapping: dict) -> dict:
    def translate(mapping, dict_to_translate):
        result = {}
        for key, value in mapping.items():
            if isinstance(value, dict):
                result[key] = translate(value, dict_to_translate)
            else:
                local_key = key.split('_')[0]
                if local_key in dict_to_translate:
                    nested_value = dict_to_translate[local_key]
                    if 'unit' in key:
                        nested_value = re.sub(r'[^a-zA-Z]', '', nested_value)
                    elif 'value' in key:
                        nested_value = re.sub(r'[^0-9.]', '', nested_value)
                    set_nested_value(result, value.split('.'), nested_value)
                else:
                    set_nested_value(result, key.split('.'), None)

        return result

    return translate(mapping, lis_dict)


def translate_generic(input_dict: dict, mapping_doc: dict) -> dict:
    """
    I have one dictionary whit this sctructure:


    { key : value }

    another dictionary which I call the mapping document has  the following structure

    {key: "categoryA.categoryB.categoryC.[can continue depending on key]"}

    my goal is to use the mapping document to assing  anew dictionary with this structure:

    {categoryA : {categoryB : { .... {categoryLast : value}

    """
    result = {}

    for key, value in input_dict.items():
        if key not in mapping_doc:
            continue  # Skip keys not found in the mapping document

        # Get the path from the mapping document and split it into categories
        path = mapping_doc[key].split(".")

        # Initialize a pointer to the current level of the result dictionary
        current_level = result

        # Iterate through the categories in the path
        for category in path[:-1]:
            if category not in current_level:
                current_level[category] = {}  # Create a new level if it doesn't exist
            current_level = current_level[category]  # Move to the next level

        # Assign the value to the deepest level
        current_level[path[-1]] = value

    return result

