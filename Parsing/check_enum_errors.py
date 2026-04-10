import json, subprocess, sys, os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

result = subprocess.run(
    [sys.executable, 'bin/validate_json.py', '--input-dir',
     'Data/BAMDataset_v032026/_batch_translated',
     '--schema', '../Data Schema/2026-04_Data-Schema_Creep_v2.1.2.json',
     '--format', 'json'],
    capture_output=True, text=True
)
data = json.loads(result.stdout)
msgs = {}
for r in data.get('reports', []):
    for e in r.get('schema_errors', []):
        key = e['data_path'][:100]
        if key not in msgs:
            msgs[key] = e['message']

for path in sorted(msgs):
    print(f"PATH: {path}")
    print(f"  MSG: {msgs[path]}")
    print()
print(f"Total unique error paths: {len(msgs)}")
