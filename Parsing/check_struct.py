import json
with open('Data/BAMDataset_v032026/_batch_translated/Vh5205_C-95-MD-TR_schema_v2.json', 'r', encoding='utf-8') as f:
    d = json.load(f)
md = d.get('MeasurementData', {})
print('MeasurementData keys:', list(md.keys()))
am = md.get('AdditionalMetadata', {})
print('AdditionalMetadata keys:', list(am.keys()))
mhc = am.get('MaterialHistoryAndCondition', {})
print('MaterialHistoryAndCondition keys:', list(mhc.keys()))
cc = mhc.get('chemicalComposition', [])
print('chemicalComposition items:', len(cc))
