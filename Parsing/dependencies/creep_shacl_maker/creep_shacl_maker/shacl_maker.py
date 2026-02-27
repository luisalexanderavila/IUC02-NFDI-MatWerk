import json
import os
import sys
import logging
import pdb
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(os.path.basename(__file__))


header_file  = os.path.join(os.path.dirname(__file__), 'header.ttl') # 'shaclShapes_Graph_small_exampl.ttl')

with open(header_file, 'r') as head:
    header = head.readlines()

def get_tesStandardParagraph(thetestandard):
    paragraph_id = '_'.join(thetestandard.split()) 
    paragraph = [
        f":{paragraph_id} :TestStandard;\n",
        f":testStandardApplied \"True\"^^xsd:boolean ;\n",
        f":testStandard \"{thetestandard}\"^^xsd:string.\n",
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

    paragraph_id = f'InitialStress_{initialstress_value}_{initialstress_unit}'
    paragraph = [
    f':{paragraph_id} a :Quality;\n',
    f'  :hasSpecifiedNumericValue \"{initialstress_value}\"^^xsd:float;\n'
    f'  :hasUnit \"{initialstress_unit}\"^^xsd:string.\n'
    ]
    return paragraph

def get_digitalMaterialIdParagraph(theDigitalID): 
    #:CMSX-6 a :TestedMaterial;
    #    :digitalMaterialIdentifier "CMSX-6"^^xsd:string.
    #
    digitalmaterialid_value = theDigitalID
    paragraph_id = [
    f':{digitalmaterialid_value} a : TestedMaterial;\n',
    f'  :digitalMaterialIdentifier \"{digitalmaterialid_value}\"^^xsd:string.\n'
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
    f':TypeOfLoading :typeOfLoading \"{theTypeOfLoading}\"^^xsd:string.\n'
    ]
    return paragraph_typeOfLoading
    #
def get_descManufacturingProc_paragraph(theDescManufacturingProc):
    #:DescriptionOfManufacturingProcess :hasDescription "Description of the manufacturing process - as-tested material. Single Crystal Investment Casting from a Vacuum Induction Refined Ingot and subsequent Heat Treatment (annealed and aged)."^^xsd:string.
    paragraph_descManufacturingProc = [
            f':DescriptionOfManufacturingProcess :hasDescription \"{theDescManufacturingProc}\"^^xsd:string.\n'
            ]
    return paragraph_descManufacturingProc

    #
    #
def get_testJob_paragraph(theTestId):
    #:TestJob :TestID "Vh5205_C-78"^^xsd:string.
    paragraph_testJob = [
            f':TestJob :TestID \"{theTestId}\"^^xsd:string.\n'
            ]
    return paragraph_testJob
    #
    #
def get_DateOfStart_paragraph(theDateOfStart):
    #:TestJob :dateOfTestStart "2023-08-02T09:06"^^xsd:dateTime.
    paragraph_DateOfStart = [
            f':TestJob :dateOfTestStart \"{theDateOfStart}\"^^xsd:dateTime.\n'
            ]
    return paragraph_DateOfStart

def write_shacl_metadata(json_metadata):
    parent = json_metadata['testInfo']['testParameters']#['materialHistoryAndConditions']
    if 'testStandard' in parent:
        teststandard = parent['testStandard']
        if not isinstance(teststandard, str):
            logger.error(' testStandard is not a string ')
            sys.exit(1)
        test_standard_paragraph = get_tesStandardParagraph(teststandard)

    parent = json_metadata['testInfo']['testParameters']
    if 'initialStress' in parent:
        initialStress = parent['initialStress']
        initialStress_paragraph = get_initalStressParagraph(initialStress)
    if 'specifiedTemperature' in parent:
        specifiedTemperature = parent['specifiedTemperature']
        specifiedTemperature_paragraph = get_specifiedTempParagraph(specifiedTemperature)
    if 'typeOfLoading' in parent:
        typeOfLoading = parent['typeOfLoading']
        typeOfLoading_paragraph = get_typeOfLoading_paragraph(typeOfLoading)

    parent = json_metadata['testInfo']['materialRelated']['materialHistoryAndCondition']
    if 'digitalMaterialID' in parent:
        digitalMaterialID = parent['digitalMaterialID']
        digitalMaterialIdParagraph = get_digitalMaterialIdParagraph(digitalMaterialID)

    parent = json_metadata['testInfo']['testJobDetails']        
    if 'dateOfTestStart' in parent:
        dateOfStart = parent['dateOfTestStart']
        dateOfStart_paragraph = get_DateOfStart_paragraph(dateOfStart)
    if 'testID' in parent:
        testID = parent['testID']
        testJob_paragraph = get_testJob_paragraph(testID)



        
    data_block = \
        test_standard_paragraph+['\n']+\
        initialStress_paragraph+['\n']+\
        digitalMaterialIdParagraph+['\n']+\
        specifiedTemperature_paragraph+['\n']+\
        typeOfLoading_paragraph+['\n']+\
        dateOfStart_paragraph+['\n']+\
        testJob_paragraph+['\n']

    return data_block



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('input_json', type=str, help='input json file with  creep test metadata')
    parser.add_argument('-o', '--output', type=str, dest='output_ttl',  help='output shacl file', default=None)
    args = parser.parse_args()
    if args.output_ttl is None:
        args.output_ttl = os.path.splitext(args.input_json)[0] + '.ttl'
    
    logger.info(f'input json file: {args.input_json}')
    logger.info(f'output json file: {args.output_ttl}')

    with open(args.input_json, 'r') as f:
        json_metadata = json.load(f)
    logger.info(f'keys : {json_metadata.keys()}')
    json_metadata = json_metadata['mappedMeasurementData']["MeasurementData"]["additionalMetadata"]

    shacl_metadata = write_shacl_metadata(json_metadata)

    with open(args.output_ttl, 'w') as f:
        f.writelines(header)
        f.writelines(shacl_metadata)

		


    #

