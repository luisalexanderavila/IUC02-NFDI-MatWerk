import sys
sys.path.insert(0, 'bin')
import importlib, validation_core
importlib.reload(validation_core)
import json
from pathlib import Path

schema_path = Path('../Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json')
data_path = Path('Data/BAMDataset_v032026/_batch_translated/Vh5205_C-95-MD-TR_schema_v2.json')

with open(schema_path, 'r', encoding='utf-8') as f:
    schema = json.load(f)
with open(data_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

req_paths, warnings, _, _ = validation_core.validate_required_keywords(schema, data)
print(f'Required paths checked: {len(req_paths)}')
print(f'Warnings (missing/empty): {len(warnings)}')
for w in warnings[:20]:
    print(f'  {w["path"]} -> {w["reason"]}')
