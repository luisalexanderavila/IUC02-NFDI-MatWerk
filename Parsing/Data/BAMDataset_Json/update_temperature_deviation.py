import json
import re
import glob
import os

folder = os.path.dirname(__file__)
files = glob.glob(os.path.join(folder, 'Vh5205_C-*-MD-TR_translated.json'))

for file_path in files:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Update dataAcquisition
    tms = data.get('MeasurementData', {}).get('AdditionalMetadata', {}).get('MeasuringAndTestEquipment', {}).get('temperatureMeasuringSystem', {})
    if 'dataAcquisition' in tms and 'temperatureDeviation' in tms['dataAcquisition']:
        value = tms['dataAcquisition']['temperatureDeviation']['value']
        value = re.sub(r'\) (\+|-)', r'); \1', value)
        data['MeasurementData']['AdditionalMetadata']['MeasuringAndTestEquipment']['temperatureMeasuringSystem']['dataAcquisition']['temperatureDeviation']['value'] = value
    
    # Update temperatureSensor
    if 'temperatureSensor' in tms and 'temperatureDeviation' in tms['temperatureSensor']:
        value = tms['temperatureSensor']['temperatureDeviation']['value']
        value = re.sub(r'\) (\+|-)', r'); \1', value)
        if ' T-values' in value:
            value = value.replace(' T-values', '; T-values')
        data['MeasurementData']['AdditionalMetadata']['MeasuringAndTestEquipment']['temperatureMeasuringSystem']['temperatureSensor']['temperatureDeviation']['value'] = value
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)