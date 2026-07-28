import json
import os
import sys
import logging
import re
from datetime import datetime
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(__file__))


header_file  = os.path.join(os.path.dirname(__file__), 'header.ttl') # 'shaclShapes_Graph_small_exampl.ttl')

with open(header_file, 'r') as head:
    header = head.readlines()


def _sanitize_local_name(value, fallback='id'):
    text = str(value).strip()
    text = re.sub(r'\s+', '_', text)
    text = re.sub(r'[^A-Za-z0-9_-]', '_', text)
    text = re.sub(r'_+', '_', text).strip('_')
    if not text:
        text = fallback
    if not re.match(r'^[A-Za-z_]', text):
        text = f'_{text}'
    return text


def _escape_literal(value):
    return str(value).replace('\\', '\\\\').replace('"', '\\"')


def _normalize_datetime_literal(value):
    raw = str(value).strip()
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw).strftime('%Y-%m-%dT%H:%M:%S')
    except ValueError:
        pass

    formats = [
        '%d.%m.%y %I:%M %p',
        '%d.%m.%Y %I:%M %p',
        '%d.%m.%y %H:%M',
        '%d.%m.%Y %H:%M',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%dT%H:%M',
        '%Y-%m-%dT%H:%M:%S',
    ]
    for date_format in formats:
        try:
            return datetime.strptime(raw, date_format).strftime('%Y-%m-%dT%H:%M:%S')
        except ValueError:
            continue

    compact_match = re.match(r'^(\d{1,2})\.(\d{1,2})\.(\d{2})(\d{1,2})(\d{2})$', raw)
    if compact_match:
        day, month, year_two_digits, hour, minute = compact_match.groups()
        try:
            parsed = datetime.strptime(
                f'{day}.{month}.{year_two_digits} {hour}:{minute}',
                '%d.%m.%y %H:%M'
            )
            return parsed.strftime('%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return None

    return None

def get_tesStandardParagraph(thetestandard):
    paragraph_id = _sanitize_local_name(thetestandard, fallback='TestStandard')
    test_standard_literal = _escape_literal(thetestandard)
    paragraph = [
        f":{paragraph_id} a :TestStandard ;\n",
        f":testStandardApplied \"True\"^^xsd:boolean ;\n",
        f":testStandard \"{test_standard_literal}\"^^xsd:string.\n",
        ]
    return paragraph 

def get_initalStressParagraph(theInitialStress):
    if 'value' not in theInitialStress:
        logger.error('initialStress value is missing')
        sys.exit(1)
    if 'unit' not in theInitialStress:
        logger.error('initialStress unit is missing')
        sys.exit(1)

    try:
        initialstress_value = float(theInitialStress['value'])
    except ValueError as E:
        logger.error('initialStress is not a float')
    initialstress_unit = theInitialStress['unit']

    paragraph_id = _sanitize_local_name(f'InitialStress_{initialstress_value}_{initialstress_unit}', fallback='InitialStress')
    paragraph = [
    f':{paragraph_id} a :Quality;\n',
    f'  :hasSpecifiedNumericValue \"{initialstress_value}\"^^xsd:float;\n'
    f'  :hasUnit \"{_escape_literal(initialstress_unit)}\"^^xsd:string.\n'
    ]
    return paragraph

def get_digitalMaterialIdParagraph(theDigitalID): 
    #:CMSX-6 a :TestedMaterial;
    #    :digitalMaterialIdentifier "CMSX-6"^^xsd:string.
    #
    digitalmaterialid_value = str(theDigitalID)
    paragraph_id = _sanitize_local_name(digitalmaterialid_value, fallback='TestedMaterial')
    paragraph_id = [
    f':{paragraph_id} a :TestedMaterial ;\n',
    f'  :digitalMaterialIdentifier \"{_escape_literal(digitalmaterialid_value)}\"^^xsd:string.\n'
    ]
    return paragraph_id

def get_specifiedTempParagraph(theSpecifiedTemp):
    #:SpecifiedTemperature a :Quality;	
    #        :hasSpecifiedNumericValue "980"^^xsd:float;
    #        :hasUnit "°C"^^xsd:string.	
    #
    if 'value' not in theSpecifiedTemp:
        logger.error('specifiedTemperature value is missing')
        sys.exit(1)
    if 'unit' not in theSpecifiedTemp:
        logger.error('specifiedTemperature unit is missing')
        sys.exit(1)
    try: 
        temp_value = float(theSpecifiedTemp['value'])
    except ValueError as E:
        logger.error('specifiedTemperature is not a float')
        sys.exit(1)
    paragraph_temp = [
            f':SpecifiedTemperature a :Quality;\n',
            f'   :hasSpecifiedNumericValue \"{temp_value}\"^^xsd:float;\n',
            f"   :hasUnit \"{theSpecifiedTemp['unit']}\"^^xsd:string.\n"
            ]
    return paragraph_temp


def get_typeOfLoading_paragraph(theTypeOfLoading):
    #:TypeOfLoading :typeOfLoading "Tension"^^xsd:string.
    paragraph_typeOfLoading = [
    f':TypeOfLoading :typeOfLoading \"{_escape_literal(theTypeOfLoading)}\"^^xsd:string.\n'
    ]
    return paragraph_typeOfLoading
    #
def get_descManufacturingProc_paragraph(theDescManufacturingProc):
    #:DescriptionOfManufacturingProcess :hasDescription "Description of the manufacturing process - as-tested material. Single Crystal Investment Casting from a Vacuum Induction Refined Ingot and subsequent Heat Treatment (annealed and aged)."^^xsd:string.
    paragraph_descManufacturingProc = [
            f':DescriptionOfManufacturingProcess :hasDescription \"{_escape_literal(theDescManufacturingProc)}\"^^xsd:string.\n'
            ]
    return paragraph_descManufacturingProc

    #
    #
def get_testJob_paragraph(theTestId):
    #:TestJob :TestID "Vh5205_C-78"^^xsd:string.
    paragraph_testJob = [
            f':TestJob :TestID \"{_escape_literal(theTestId)}\"^^xsd:string.\n'
            ]
    return paragraph_testJob
    #
    #
def get_DateOfStart_paragraph(theDateOfStart):
    #:TestJob :dateOfTestStart "2023-08-02T09:06"^^xsd:dateTime.
    normalized = _normalize_datetime_literal(theDateOfStart)
    if normalized is not None:
        literal = normalized
        datatype = 'xsd:dateTime'
    else:
        logger.warning(f'Could not normalize dateOfTestStart "{theDateOfStart}" to xsd:dateTime; writing xsd:string')
        literal = str(theDateOfStart)
        datatype = 'xsd:string'
    paragraph_DateOfStart = [
            f':TestJob :dateOfTestStart \"{_escape_literal(literal)}\"^^{datatype}.\n'
            ]
    return paragraph_DateOfStart

def write_shacl_metadata(json_metadata):
    test_standard_paragraph = []
    initialStress_paragraph = []
    specifiedTemperature_paragraph = []
    typeOfLoading_paragraph = []
    digitalMaterialIdParagraph = []
    dateOfStart_paragraph = []
    testJob_paragraph = []

    parent = json_metadata['testInfo']['testParameters']
    if 'testStandard' in parent:
        test_standard_paragraph = get_tesStandardParagraph(str(parent['testStandard']))
    if 'initialStress' in parent:
        initialStress_paragraph = get_initalStressParagraph(parent['initialStress'])
    if 'specifiedTemperature' in parent:
        specifiedTemperature_paragraph = get_specifiedTempParagraph(parent['specifiedTemperature'])
    if 'typeOfLoading' in parent:
        typeOfLoading_paragraph = get_typeOfLoading_paragraph(parent['typeOfLoading'])

    parent = json_metadata['testInfo']['materialRelated']['materialHistoryAndCondition']
    if 'digitalMaterialID' in parent:
        digitalMaterialIdParagraph = get_digitalMaterialIdParagraph(parent['digitalMaterialID'])

    parent = json_metadata['testInfo']['testJobDetails']
    if 'dateOfTestStart' in parent:
        dateOfStart_paragraph = get_DateOfStart_paragraph(parent['dateOfTestStart'])
    if 'testID' in parent:
        testJob_paragraph = get_testJob_paragraph(parent['testID'])

    data_block = (
        test_standard_paragraph + ['\n'] +
        initialStress_paragraph + ['\n'] +
        digitalMaterialIdParagraph + ['\n'] +
        specifiedTemperature_paragraph + ['\n'] +
        typeOfLoading_paragraph + ['\n'] +
        dateOfStart_paragraph + ['\n'] +
        testJob_paragraph + ['\n']
    )
    return data_block




