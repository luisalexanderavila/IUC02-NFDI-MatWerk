import json
import os

# Load the JSON data
def read_mapping(file_path: os.PathLike) -> dict:

    with open(file_path, 'r') as file:
        data = json.load(file)

    def set_nested_value(d, keys, value):
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value

    result = {}
    for key, value in data.items():
        keys = key.split('.')
        set_nested_value(result, keys, value)

    # Print the resulting nested dictionary
    return result
#    print(json.dumps(result, indent=4))