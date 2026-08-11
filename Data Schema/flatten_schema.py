import json

def flatten_dropdowns(obj):
    if isinstance(obj, dict):
        for key, value in list(obj.items()):
            if isinstance(value, dict) and 'type' in value and value['type'] == 'object' and 'properties' in value:
                props = value['properties']
                if len(props) == 1:
                    inner_key = list(props.keys())[0]
                    if inner_key.endswith('Options') and isinstance(props[inner_key], dict) and 'type' in props[inner_key] and props[inner_key]['type'] == 'string' and 'enum' in props[inner_key]:
                        # It's a dropdown
                        new_key = inner_key[:-7]  # remove 'Options'
                        obj[key] = props[inner_key].copy()
                        if 'allOf' in value:
                            # Adjust allOf
                            allof = value['allOf']
                            for item in allof:
                                if 'if' in item and 'properties' in item['if']:
                                    if inner_key in item['if']['properties']:
                                        item['if']['properties'][new_key] = item['if']['properties'].pop(inner_key)
                        if 'allOf' in obj[key]:
                            # If allOf is now on the string, but since it's string, perhaps remove or adjust
                            # For now, keep it, but it might not be valid
                            pass
                        # Remove the object wrapper
                        del obj[key]
                        obj[new_key] = props[inner_key].copy()
                        if 'allOf' in value:
                            obj[new_key]['allOf'] = value['allOf']
            else:
                flatten_dropdowns(value)
    elif isinstance(obj, list):
        for item in obj:
            flatten_dropdowns(item)

# Load the JSON
with open('c:\\Users\\lavila\\iuc02\\iuc02\\Data Schema\\2026-04_Data-Schema_Creep_v2.1.2.json', 'r') as f:
    data = json.load(f)

# Flatten
flatten_dropdowns(data)

# Save
with open('c:\\Users\\lavila\\iuc02\\iuc02\\Data Schema\\2026-04_Data-Schema_Creep_v2.1.2.json', 'w') as f:
    json.dump(data, f, indent=2)